# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0012 with ADR 0013: a room restored from the store in the middle of a private turn keeps the deadline its record
implies. A restart neither restarts the countdown nor loses it; a deadline that passed while the server was down fires
at once, and the server's commit is on disk like any other move."""

from __future__ import annotations

import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from fairflow_engine import audit
from fastapi.testclient import TestClient
from test_private_timer import (
    DECISION_S,
    GRACE_S,
    TIMER_TICK_S,
    Clock,
    commit,
    open_private_turn,
    opened,
    roles_of,
    wait_for_phase,
)
from test_server import connect, open_room
from test_store import HOUR, rows, settings

from fairflow_server.app import create_app


def play_to_private_turn(tmp_path: Path, clock: Clock) -> tuple[str, list[str], float]:
    """Open a room on a store, open season 1's private turn and let every scheme but the last commit; then stop.
    Returns the room, its schemes and the record time the private turn opened."""
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        info = open_room(client)
        roles = roles_of(info)
        with ExitStack() as stack:
            sockets = {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]}
            open_private_turn(sockets, roles)
            sockets.pop(roles[-1]).close()
            for r in roles[:-1]:
                commit(sockets, r)
        start = opened(client, info["room"])
    return info["room"], roles, start


def events(client: TestClient, code: str) -> list[dict[str, Any]]:
    return list(client.app.state.registry.get(code).game.events)  # type: ignore[attr-defined]


def test_a_deadline_that_passed_while_the_server_was_down_fires_on_restart(tmp_path: Path) -> None:
    clock = Clock()
    code, roles, start = play_to_private_turn(tmp_path, clock)
    clock.t = start + DECISION_S + GRACE_S + TIMER_TICK_S  # the server was down past the deadline
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        assert wait_for_phase(client, code, ("reveal", "ended")) in ("reveal", "ended")
        record = events(client, code)
        setup = client.app.state.registry.get(code).game.setup  # type: ignore[attr-defined]
    plays = [e["payload"] for e in record if e["type"] == "action.played"]
    assert [p.get("autoCommittedBy") for p in plays] == [None] * (len(roles) - 1) + ["server"]
    assert [p for p in audit(setup, record) if not p.startswith("note:")] == []
    with TestClient(create_app(settings(tmp_path), now=clock)) as again:  # the server's commit was written to the store
        assert events(again, code) == record


def test_a_restart_before_the_deadline_keeps_the_deadline_from_the_record(tmp_path: Path) -> None:
    clock = Clock()
    code, _, start = play_to_private_turn(tmp_path, clock)
    clock.t = start + DECISION_S + GRACE_S - 2 * TIMER_TICK_S  # test input: restarted shortly before the deadline
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        assert client.get(f"/rooms/{code}").json()["phase"] == "private"
        # a countdown restarted at the restart would need the whole decision time again; the record's needs two ticks
        clock.t += 2 * TIMER_TICK_S
        assert wait_for_phase(client, code, ("reveal", "ended")) in ("reveal", "ended")
        assert events(client, code)[-1]["type"] in ("season.resolved", "game.ended", "goal.result")


def test_a_restored_room_whose_turn_was_complete_gets_no_timer(tmp_path: Path) -> None:
    clock = Clock()
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        info = open_room(client)
        roles = roles_of(info)
        with ExitStack() as stack:
            sockets = {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]}
            open_private_turn(sockets, roles)
            for r in roles:
                commit(sockets, r)
        before = events(client, info["room"])
    clock.t += DECISION_S + GRACE_S + TIMER_TICK_S
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        time.sleep(2 * TIMER_TICK_S)  # test input: two ticks in which nothing may happen
        assert events(client, info["room"]) == before


def test_a_room_past_its_ttl_is_not_restored_and_its_timer_does_not_revive_it(tmp_path: Path) -> None:
    """ADR 0012: a room whose last move is more than the TTL old when the server starts is not served again. Its open
    private turn's deadline has long passed too, but the server must not commit for it: that would be a new last move."""
    clock = Clock()
    code, _, start = play_to_private_turn(tmp_path, clock)
    clock.t = start + settings(tmp_path).room_ttl_hours * HOUR + DECISION_S + GRACE_S  # the server was down this long
    app = create_app(settings(tmp_path), now=clock)
    with TestClient(app) as client:
        time.sleep(2 * TIMER_TICK_S)  # test input: two ticks for any timer to act
        assert code not in app.state.registry.rooms
        assert client.get(f"/rooms/{code}").status_code == 404
    assert rows(settings(tmp_path).store_path)["rooms"] == 0  # type: ignore[arg-type]
