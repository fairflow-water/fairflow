# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R7 over the wire (issue #34): a scheme phone that sends `propose` is refused by the engine and nothing is recorded;
the facilitator's proposal reaches every screen."""

from __future__ import annotations

import json
from contextlib import ExitStack
from typing import Any

from fastapi.testclient import TestClient
from test_private_timer import SETTINGS, Clock, act, record, roles_of
from test_server import connect, open_room

from fairflow_server.app import create_app


def test_a_scheme_phone_cannot_propose() -> None:
    with TestClient(create_app(SETTINGS, now=Clock())) as client:
        info = open_room(client)
        roles = roles_of(info)
        with ExitStack() as stack:
            sockets: dict[str, Any] = {
                w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]
            }
            act(sockets, "authority", {"intent": "start_season"})
            sockets[roles[0]].send_text(json.dumps({"intent": "propose", "lens": "proportional"}))
            refusal = sockets[roles[0]].receive_json()
            assert (refusal["type"], refusal["code"]) == ("rejected", "not_authority")
            sockets["authority"].send_text(json.dumps({"intent": "propose", "lens": "proportional"}))
            for who, ws in sockets.items():
                msg = ws.receive_json()
                assert msg["type"] == "events" and [e["type"] for e in msg["events"]] == ["lens.proposed"], who
        proposed = [e for e in record(client, info["room"]) if e["type"] == "lens.proposed"]
        assert [e["actor"] for e in proposed] == ["authority"]
