# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R3, §6.2 `linking.code` (ADR 0016, proposed) over the wire: a scheme joins with its linking code; the code reaches
that scheme's own phone in its sync and no other screen, the facilitator and the projector included."""

import json
from contextlib import ExitStack
from typing import Any

from fastapi.testclient import TestClient
from test_server import ORIGIN, client, join_body

__all__ = ["client"]  # the shared fixture

CODE = "AB03"  # test input: a participant-made code (blueprint §6.2 example: mother's initials + birth month)


def synced(client: TestClient, stack: ExitStack, room: str, token: str) -> list[dict[str, Any]]:
    ws = stack.enter_context(client.websocket_connect(f"/rooms/{room}/ws", headers={"origin": ORIGIN}))
    ws.send_text(json.dumps({"token": token}))
    assert ws.receive_json()["type"] == "welcome"
    sync = ws.receive_json()
    assert sync["type"] == "sync"
    return list(sync["events"])


def test_a_code_reaches_its_own_phone_only(client: TestClient) -> None:
    room = client.post("/rooms", json={"scenario": "default-basin"}).json()
    code, free = room["room"], client.get(f"/rooms/{room['room']}").json()["freeRoles"]
    tokens = {"authority": room["facilitatorToken"], "display": room["displayToken"]}
    for i, role in enumerate(free):
        body = join_body(role, f"hash-{role}-0123") | ({"linkingCode": CODE} if i == 0 else {})
        r = client.post(f"/rooms/{code}/join", json=body)
        assert r.status_code == 200
        tokens[role] = r.json()["token"]
    with ExitStack() as stack:
        seen = {who: synced(client, stack, code, token) for who, token in tokens.items()}
    for who, events in seen.items():
        carries = any(e["type"] == "linking.code" for e in events)
        assert carries == (who == free[0]), who
        assert (CODE in str(events)) == (who == free[0]), who


def test_a_malformed_code_is_refused_and_the_seat_stays_free(client: TestClient) -> None:
    room = client.post("/rooms", json={"scenario": "default-basin"}).json()
    code = room["room"]
    role = client.get(f"/rooms/{code}").json()["freeRoles"][0]
    r = client.post(f"/rooms/{code}/join", json=join_body(role, "hash-x-0123") | {"linkingCode": "ab 03"})
    assert r.status_code >= 400 and "bad_linking_code" in r.text
    assert role in client.get(f"/rooms/{code}").json()["freeRoles"]
