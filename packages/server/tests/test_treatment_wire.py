# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R1 and ADR 0018 over the wire: the facilitator sets the Authority hand-over season when opening a room (0 = never);
left out, the scenario's default is used. Every room's record carries `treatment.assigned` before season 1, and every
connection receives it. A season outside the game is refused, and no room is made."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_server import ORIGIN, client

__all__ = ["client"]  # the shared fixture
SCENARIO = json.loads((Path(__file__).resolve().parents[2] / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))
DEFAULT = SCENARIO["treatments"]["authorityHandoverSeason"]
LONGEST = SCENARIO["basin"]["gameLength"]["max"]


def arms(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    r = client.post("/rooms", json={"scenario": "default-basin", **body})
    assert r.status_code == 200, r.text
    room = r.json()
    with ExitStack() as stack:
        ws = stack.enter_context(client.websocket_connect(f"/rooms/{room['room']}/ws", headers={"origin": ORIGIN}))
        ws.send_text(json.dumps({"token": room["displayToken"]}))
        assert ws.receive_json()["type"] == "welcome"
        sync = ws.receive_json()
    types = [e["type"] for e in sync["events"]]
    assert types.index("treatment.assigned") == 1  # right after game.created, before any season
    [e] = [e for e in sync["events"] if e["type"] == "treatment.assigned"]
    return dict(e["payload"])


def test_left_out_the_scenario_default_is_recorded(client: TestClient) -> None:
    payload = arms(client, {})
    assert payload["authorityHandoverSeason"] == DEFAULT
    assert payload["assignedBy"] == "facilitator"
    assert not (payload["silentMode"] or payload["secretBallot"] or payload["universalisationNudge"])


@pytest.mark.parametrize("season", [0, LONGEST - 1])
def test_the_facilitator_sets_the_hand_over_season(client: TestClient, season: int) -> None:
    assert arms(client, {"authorityHandoverSeason": season})["authorityHandoverSeason"] == season


@pytest.mark.parametrize(("season", "status"), [(-1, 409), (LONGEST, 409), ("2", 422), (True, 422)])
def test_a_season_outside_the_game_is_refused_and_no_room_is_made(client: TestClient, season: Any, status: int) -> None:
    rooms = len(client.app.state.registry.rooms)  # type: ignore[attr-defined]
    r = client.post("/rooms", json={"scenario": "default-basin", "authorityHandoverSeason": season})
    assert r.status_code == status
    if status == 409:
        assert r.json()["detail"]["code"] == "bad_treatment"
    assert len(client.app.state.registry.rooms) == rooms  # type: ignore[attr-defined]
