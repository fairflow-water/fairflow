# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0018 decision 2, issue #9, over the wire: the Authority's device makes a one-time link that moves a role to
another phone; the new phone claims it with its own device hash. The move is recorded and broadcast, the new phone
plays the role, and the old phone's token, a used link and a replaced link stop working. A link's token is never a
way in. The store keeps none of the revoked tokens, so a restart does not bring them back."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from test_server import ORIGIN, client, connect, open_room
from test_store import Clock, settings

from fairflow_server.app import ROLE_MOVED, create_app
from fairflow_server.rooms import RoomRegistry

__all__ = ["client"]  # the shared fixture
NEW_PHONE = "hash-new-phone-0123"  # test input: the claiming phone's device hash


def offer(client: TestClient, room: str, token: str, role: str) -> Any:
    return client.post(f"/rooms/{room}/transfers", json={"token": token, "role": role})


def claim(client: TestClient, room: str, link: str, device: str = NEW_PHONE) -> Any:
    return client.post(f"/rooms/{room}/transfers/claim", json={"link": link, "deviceHash": device})


def refused(client: TestClient, room: str, token: str) -> int:
    """The close code a connection with this token gets."""
    with client.websocket_connect(f"/rooms/{room}/ws", headers={"origin": ORIGIN}) as ws:
        ws.send_text(json.dumps({"token": token}))
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
    return e.value.code


def test_only_the_authority_makes_a_link(client: TestClient) -> None:
    info = open_room(client)
    r = offer(client, info["room"], info["A"], "B")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_authority"
    r = offer(client, info["room"], info["authority"], "Z")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_seated"


def test_a_scheme_moves_and_its_old_phone_is_told_and_shut_out(client: TestClient) -> None:
    info = open_room(client)
    room = info["room"]
    link = offer(client, room, info["authority"], "A").json()["link"]
    with ExitStack() as stack:
        old = connect(client, stack, room, info["A"])
        projector = connect(client, stack, room, info["display"])
        moved = claim(client, room, link)
        assert moved.status_code == 200 and moved.json()["role"] == "A"
        with pytest.raises(WebSocketDisconnect) as e:
            old.receive_json()
        assert e.value.code == ROLE_MOVED
        update = projector.receive_json()
        assert [x["type"] for x in update["events"]] == ["seat.transferred"]
        assert update["events"][0]["payload"]["toDevice"] == NEW_PHONE
        connect(client, stack, room, moved.json()["token"])  # the new phone plays the role
    assert refused(client, room, info["A"]) == 1008  # the old token no longer works
    assert claim(client, room, link).json()["detail"]["code"] == "unknown_transfer"  # a link works once


def test_the_authority_hands_over(client: TestClient) -> None:
    info = open_room(client)
    room = info["room"]
    link = offer(client, room, info["authority"], "authority").json()["link"]
    new = claim(client, room, link).json()
    assert new["role"] == "authority"
    with ExitStack() as stack:
        ws = connect(client, stack, room, new["token"])
        ws.send_text(json.dumps({"intent": "start_season"}))  # the new phone acts as the Authority
        assert ws.receive_json()["events"][0]["type"] == "season.climate"
    assert refused(client, room, info["authority"]) == 1008


def test_a_link_is_never_a_way_in_and_a_newer_one_replaces_it(client: TestClient) -> None:
    info = open_room(client)
    room = info["room"]
    first = offer(client, room, info["authority"], "B").json()["link"]
    assert refused(client, room, first) == 1008
    second = offer(client, room, info["authority"], "B").json()["link"]
    assert claim(client, room, first).json()["detail"]["code"] == "unknown_transfer"
    assert claim(client, room, second).status_code == 200


def test_the_store_keeps_no_revoked_token(tmp_path: Path) -> None:
    clock = Clock()
    with TestClient(create_app(settings(tmp_path), now=clock)) as c:
        info = open_room(c)
        link = offer(c, info["room"], info["authority"], "C").json()["link"]
        new = claim(c, info["room"], link).json()["token"]
    reg = RoomRegistry(settings(tmp_path), now=clock)  # a restart, from the file alone
    room = reg.get(info["room"])
    assert room.role_of(new) == "C"
    assert room.role_of(info["C"]) is None and room.role_of(link) is None


def test_an_intent_from_the_old_phone_after_the_move_is_refused(client: TestClient) -> None:
    """An old phone's intent can be waiting for the room lock while the move happens; once it gets the lock, it must
    be refused, not played as the role. Here the move is made directly, so the old socket is still open when it sends."""
    info = open_room(client)
    room = info["room"]
    registry = client.app.state.registry  # type: ignore[attr-defined]
    with ExitStack() as stack:
        old = connect(client, stack, room, info["authority"])
        link = registry.offer_transfer(room, info["authority"], "authority")
        registry.claim_transfer(room, link, NEW_PHONE)
        before = len(registry.get(room).game.events)
        old.send_text(json.dumps({"intent": "start_season"}))
        with pytest.raises(WebSocketDisconnect) as e:
            old.receive_json()
        assert e.value.code == ROLE_MOVED
        assert len(registry.get(room).game.events) == before  # nothing was played
