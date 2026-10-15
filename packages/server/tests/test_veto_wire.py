# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R8 (ADR 0015) over the wire: the facilitator's veto reaches every screen; a phone's is refused by the engine."""

from __future__ import annotations

import json
from contextlib import ExitStack
from typing import Any

from fastapi.testclient import TestClient
from test_private_timer import SETTINGS, Clock, act, record, roles_of
from test_server import connect, open_room

from fairflow_server.app import create_app


def test_the_facilitator_vetoes_and_every_screen_is_told() -> None:
    with TestClient(create_app(SETTINGS, now=Clock())) as client:
        info = open_room(client)
        roles = roles_of(info)
        with ExitStack() as stack:
            sockets: dict[str, Any] = {
                w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]
            }
            act(sockets, "authority", {"intent": "start_season"})
            for lens in ("proportional", "utilitarian"):
                act(sockets, "authority", {"intent": "propose", "lens": lens})
            sockets[roles[0]].send_text(json.dumps({"intent": "veto", "lens": "utilitarian"}))
            refusal = sockets[roles[0]].receive_json()
            assert (refusal["type"], refusal["code"]) == ("rejected", "not_authority")  # only the Authority holds the veto
            sockets["authority"].send_text(json.dumps({"intent": "veto", "lens": "utilitarian"}))
            for who, ws in sockets.items():
                msg = ws.receive_json()
                assert msg["type"] == "events" and [e["type"] for e in msg["events"]] == ["lens.vetoed"], who
        vetoed = [e for e in record(client, info["room"]) if e["type"] == "lens.vetoed"]
        assert [(e["actor"], e["payload"]) for e in vetoed] == [("authority", {"lens": "utilitarian"})]
