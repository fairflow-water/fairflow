# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The room server end to end over real WebSockets: a full game, privacy of everything sent over the wire (§9.1 "no relay
message to a client other than the acting role contains W, A, Y, ΔL or P"), and the OWASP-driven protections."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from fairflow_server.app import create_app
from fairflow_server.settings import Settings

ORIGIN = "https://play.fairflow.example"  # test input
SEALED_KEYS = {"W", "A", "Y", "dL", "P", "pumpsBy", "pumpCost", "L", "stockNext", "returnFlow"}


def keys_in(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(keys_in(v) for v in obj.values()))
    if isinstance(obj, list):
        return set().union(*(keys_in(v) for v in obj))
    return set()


@pytest.fixture
def client() -> Iterator[TestClient]:
    # One TestClient context = one event loop shared by every socket, as in a real uvicorn process. Without the context
    # each WebSocket gets its own loop and cross-socket broadcasts deadlock in the harness (not in the server).
    with TestClient(create_app(Settings(allowed_origins=(ORIGIN,)))) as c:
        yield c


def open_room(client: TestClient) -> dict[str, str]:
    r = client.post("/rooms", json={"scenario": "default-basin"})
    assert r.status_code == 200
    room = r.json()
    tokens = {"authority": room["facilitatorToken"], "display": room["displayToken"]}
    for role in client.get(f"/rooms/{room['room']}").json()["freeRoles"]:
        j = client.post(
            f"/rooms/{room['room']}/join",
            json={"role": role, "deviceHash": f"hash-{role}-0123", "consentGiven": True, "presurveyComplete": True},
        )
        assert j.status_code == 200
        tokens[role] = j.json()["token"]
    return {"room": room["room"], **tokens}


def connect(client: TestClient, stack: ExitStack, room: str, token: str) -> Any:
    ws = stack.enter_context(client.websocket_connect(f"/rooms/{room}/ws", headers={"origin": ORIGIN}))
    ws.send_text(json.dumps({"token": token}))
    assert ws.receive_json()["type"] == "welcome"
    assert ws.receive_json()["type"] == "sync"
    return ws


def test_a_full_game_over_websockets_keeps_pumping_private(client: TestClient) -> None:
    info = open_room(client)
    roles = [r for r in info if r not in ("room", "authority", "display")]
    received: dict[str, list[dict[str, Any]]] = {}
    with ExitStack() as stack:
        sockets = {who: connect(client, stack, info["room"], info[who]) for who in ["authority", "display", *roles]}

        def act(who: str, message: dict[str, Any]) -> None:
            sockets[who].send_text(json.dumps(message))
            for name, ws in sockets.items():
                msg = ws.receive_json()
                assert msg["type"] in ("events", "sync"), (name, msg)
                received.setdefault(name, []).append(msg)

        ended = False
        while not ended:
            act("authority", {"intent": "start_season"})
            act("authority", {"intent": "propose", "lens": "proportional"})
            for r in roles:
                act(r, {"intent": "vote", "lens": "proportional"})
            act("authority", {"intent": "close_vote"})
            for i, r in enumerate(roles):
                act(r, {"intent": "commit", "pumps": 2.0 if i == 0 else 0.0, **({"action": "expand"} if i == 1 else {})})
            ended = any(e["type"] == "game.ended" for m in received["display"] for e in m["events"])
        before_debrief = {k: list(v) for k, v in received.items()}
        act("authority", {"intent": "open_debrief", "perPlayer": True})

    for who, messages in before_debrief.items():
        own = who if who in roles else None
        for m in messages:
            for e in m["events"]:
                if e["type"] in ("action.played", "private.opened", "goal.result"):
                    assert e["actor"] == own, f"{who} received another role's private {e['type']}"
                if e["type"] == "season.resolved":
                    assert "sealed" not in e["payload"], f"{who} received sealed season data before the debrief"
                    if own is None:
                        assert not keys_in(e["payload"]) & SEALED_KEYS, who
    debrief = received["display"][-1]
    assert debrief["type"] == "sync" and "pumpsBy" in keys_in(debrief["events"])


def test_origin_must_be_on_the_allowlist(client: TestClient) -> None:
    info = open_room(client)
    for headers in ({}, {"origin": "https://evil.example"}):
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/rooms/{info['room']}/ws", headers=headers) as ws,
        ):
            ws.receive_json()


def test_a_wrong_token_is_refused(client: TestClient) -> None:
    info = open_room(client)
    with client.websocket_connect(f"/rooms/{info['room']}/ws", headers={"origin": ORIGIN}) as ws:
        ws.send_text(json.dumps({"token": "not-a-token"}))
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 1008


def test_a_message_cannot_choose_its_actor_or_carry_unknown_fields(client: TestClient) -> None:
    info = open_room(client)
    player = next(r for r in info if r not in ("room", "authority", "display"))
    with ExitStack() as stack:
        ws = connect(client, stack, info["room"], info[player])
        ws.send_text(json.dumps({"intent": "start_season", "actor": "authority"}))
        assert ws.receive_json() == {"type": "invalid", "fields": ["start_season.actor"]}
        ws.send_text(json.dumps({"intent": "start_season"}))
        assert ws.receive_json()["code"] == "not_authority"
        ws.send_text(json.dumps({"intent": "commit", "pumps": "lots"}))
        assert ws.receive_json()["type"] == "invalid"


def test_the_display_is_read_only(client: TestClient) -> None:
    info = open_room(client)
    with ExitStack() as stack:
        ws = connect(client, stack, info["room"], info["display"])
        ws.send_text(json.dumps({"intent": "start_season"}))
        assert ws.receive_json()["code"] == "read_only"


def test_oversized_messages_close_the_connection() -> None:
    with TestClient(create_app(Settings(allowed_origins=(ORIGIN,), max_message_bytes=256))) as client, ExitStack() as stack:
        info = open_room(client)
        ws = connect(client, stack, info["room"], info["authority"])
        ws.send_text(json.dumps({"intent": "propose", "lens": "x" * 1000}))
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 1009


def test_rate_limit() -> None:
    with (
        TestClient(create_app(Settings(allowed_origins=(ORIGIN,), rate_burst=3, rate_per_second=0.001))) as client,
        ExitStack() as stack,
    ):
        info = open_room(client)
        ws = connect(client, stack, info["room"], info["display"])
        codes = []
        for _ in range(5):
            ws.send_text(json.dumps({"intent": "start_season"}))
            codes.append(ws.receive_json()["code"])
        assert codes[:3] == ["read_only"] * 3 and codes[3:] == ["rate_limited"] * 2


def test_rest_errors(client: TestClient) -> None:
    assert client.post("/rooms", json={"scenario": "../parameters"}).status_code == 404
    assert client.post("/rooms", json={"scenario": "nope"}).status_code == 404
    assert client.get("/rooms/ZZZZZ").status_code == 404
    info = open_room(client)
    again = client.post(
        f"/rooms/{info['room']}/join",
        json={"role": "A", "deviceHash": "hash-A-again", "consentGiven": True, "presurveyComplete": True},
    )
    assert again.status_code == 409
    assert client.post("/rooms", json={"scenario": "default-basin", "admin": True}).status_code == 422


def test_room_info_exposes_only_public_scenario_fields(client: TestClient) -> None:
    info = open_room(client)
    scenario = client.get(f"/rooms/{info['room']}").json()["scenario"]
    assert [s["id"] for s in scenario["schemes"]] == ["A", "B", "C"]
    assert {k for s in scenario["schemes"] for k in s} <= {"id", "name", "seat", "shape", "glyph", "crop"}
    assert scenario["lenses"][0]["plainName"] == "Biggest harvest"
