# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0014: the server times the negotiation (R7, R8, R20). On a test clock: a vote still open at the deadline applies
the previous lens (the scenario's default in season 1), recorded byTimeout; a vote closed in time is left alone; the
length follows the season; no client can send the server's intent; a restored room keeps the deadline its record
implies."""

from __future__ import annotations

import json
import time
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_private_timer import (
    REPO,
    SESSION,
    SETTINGS,
    TIMER_TICK_S,
    Clock,
    act,
    commit,
    phase,
    record,
    roles_of,
    wait_for_phase,
)
from test_server import connect, open_room
from test_store import settings

from fairflow_server.app import create_app
from fairflow_server.rooms import load_registry

LAST_SHORT_NEGOTIATION: int = load_registry(SETTINGS)["session.lastShortNegotiationSeason"]  # R20, from the registry

NEGOTIATION = SESSION["negotiationS"]
# past the vote: a clock moved past the negotiation deadline is past the private turn's too, so its timer may follow
PAST_VOTE = ("private", "reveal", "ended")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock: Clock) -> Any:
    with TestClient(create_app(SETTINGS, now=clock)) as c:
        yield c


def vote_opened(client: TestClient, room: str) -> float:
    """The record time of the open season's season.climate (the start of the negotiation, R7)."""
    event = next(e for e in reversed(record(client, room)) if e["type"] == "season.climate")
    return datetime.fromisoformat(event["t"]).timestamp()


def chosen(client: TestClient, room: str) -> list[dict[str, Any]]:
    return [e for e in record(client, room) if e["type"] == "lens.chosen"]


def length(season: int) -> float:
    return float(NEGOTIATION["seasons0to2"] if season <= LAST_SHORT_NEGOTIATION else NEGOTIATION["from3"])


def everyone(client: TestClient, stack: ExitStack, info: dict[str, str]) -> dict[str, Any]:
    return {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles_of(info)]}


def test_an_open_vote_closes_at_the_deadline_on_the_previous_lens(client: TestClient, clock: Clock) -> None:
    info = open_room(client)
    with ExitStack() as stack:
        sockets = everyone(client, stack, info)
        act(sockets, "authority", {"intent": "start_season"})
        start = vote_opened(client, info["room"])
        clock.t = start + length(1) - TIMER_TICK_S  # test input: a tick before the deadline: nothing happens
        time.sleep(2 * TIMER_TICK_S)  # test input: two ticks of the timer
        assert phase(client, info["room"]) == "vote"
        clock.t = start + length(1)
        assert wait_for_phase(client, info["room"], PAST_VOTE) in PAST_VOTE
        for who, ws in sockets.items():  # every screen is told, like any other move
            assert ws.receive_json()["type"] == "events", who
    [c] = chosen(client, info["room"])
    default = client.app.state.registry.get(info["room"]).game.setup.defaultLens  # type: ignore[attr-defined]
    assert (c["actor"], c["payload"]["lens"], c["payload"]["byTimeout"]) == ("engine", default, True)


def test_a_leader_at_the_deadline_is_not_chosen_the_previous_lens_applies(client: TestClient, clock: Clock) -> None:
    """Section 13 row 9, "previous lens everywhere" (ADR 0014): expiry applies the previous lens, in season 1 the
    scenario's default, even with a proposal that has a vote; the votes cast are recorded."""
    info = open_room(client)
    roles = roles_of(info)
    default = json.loads((REPO / "packages" / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))["defaultLens"]
    with ExitStack() as stack:
        sockets = everyone(client, stack, info)
        act(sockets, "authority", {"intent": "start_season"})
        voted = next(lens for lens in ("egalitarian", "capability") if lens != default)  # test input: not the default
        act(sockets, "authority", {"intent": "propose", "lens": voted})
        act(sockets, roles[0], {"intent": "vote", "lens": voted})
        clock.t = vote_opened(client, info["room"]) + length(1)
        assert wait_for_phase(client, info["room"], PAST_VOTE) in PAST_VOTE
    [c] = chosen(client, info["room"])
    assert (c["payload"]["lens"], c["payload"]["tally"], c["payload"]["byTimeout"]) == (default, {voted: 1}, True)


def test_a_vote_closed_in_time_is_left_alone(client: TestClient, clock: Clock) -> None:
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = everyone(client, stack, info)
        act(sockets, "authority", {"intent": "start_season"})
        act(sockets, "authority", {"intent": "propose", "lens": "proportional"})
        for r in roles:
            act(sockets, r, {"intent": "vote", "lens": "proportional"})
        act(sockets, "authority", {"intent": "close_vote"})
        clock.t = vote_opened(client, info["room"]) + length(1) + TIMER_TICK_S
        time.sleep(2 * TIMER_TICK_S)  # test input: two ticks in which the vote timer may not act
    [c] = chosen(client, info["room"])  # one choice, the Authority's close
    assert (c["actor"], c["payload"]["byTimeout"]) == ("engine", False)


def test_the_negotiation_is_longer_from_season_3(client: TestClient, clock: Clock) -> None:
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = everyone(client, stack, info)
        for _ in range(LAST_SHORT_NEGOTIATION):  # seasons 1 and 2, closed by hand
            act(sockets, "authority", {"intent": "start_season"})
            act(sockets, "authority", {"intent": "propose", "lens": "proportional"})
            act(sockets, "authority", {"intent": "close_vote"})
            for r in roles:
                commit(sockets, r)
        act(sockets, "authority", {"intent": "start_season"})
        start = vote_opened(client, info["room"])
        clock.t = start + length(LAST_SHORT_NEGOTIATION)  # the short negotiation's length: not yet in season 3
        time.sleep(2 * TIMER_TICK_S)  # test input: two ticks in which nothing may happen
        assert phase(client, info["room"]) == "vote"
        clock.t = start + length(LAST_SHORT_NEGOTIATION + 1)
        assert wait_for_phase(client, info["room"], PAST_VOTE) in PAST_VOTE
    assert [c["payload"]["byTimeout"] for c in chosen(client, info["room"])] == [False, False, True]


def test_the_last_short_season_has_the_short_negotiation(client: TestClient, clock: Clock) -> None:
    """R20: 3:00 in seasons 0-2. Season 2 (LAST_SHORT_NEGOTIATION) still closes at the short length."""
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = everyone(client, stack, info)
        for _ in range(LAST_SHORT_NEGOTIATION - 1):  # the seasons before it, closed by hand
            act(sockets, "authority", {"intent": "start_season"})
            act(sockets, "authority", {"intent": "propose", "lens": "proportional"})
            act(sockets, "authority", {"intent": "close_vote"})
            for r in roles:
                commit(sockets, r)
        act(sockets, "authority", {"intent": "start_season"})
        clock.t = vote_opened(client, info["room"]) + length(LAST_SHORT_NEGOTIATION)
        assert wait_for_phase(client, info["room"], PAST_VOTE) in PAST_VOTE
    assert [c["payload"]["byTimeout"] for c in chosen(client, info["room"])][-1] is True


def test_a_room_restored_mid_vote_after_a_proposal_keeps_the_deadline_from_the_screen_opening(tmp_path: Path) -> None:
    """R7: "the negotiation timer starts when the lens screen opens": the record time of season.climate, however long
    the table then took to propose, also for a room restored from the store (ADR 0012)."""
    clock = Clock()
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        info = open_room(client)
        with ExitStack() as stack:
            sockets = everyone(client, stack, info)
            act(sockets, "authority", {"intent": "start_season"})
            time.sleep(3 * TIMER_TICK_S)  # test input: the first proposal comes this long after the screen opened
            act(sockets, "authority", {"intent": "propose", "lens": "proportional"})
        start = vote_opened(client, info["room"])
    clock.t = start + length(1) + TIMER_TICK_S  # restarted past the screen's deadline, before a proposal's would be
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        assert wait_for_phase(client, info["room"], PAST_VOTE) in PAST_VOTE
        assert chosen(client, info["room"])[-1]["payload"]["byTimeout"] is True


def test_no_client_can_send_the_server_intent(client: TestClient) -> None:
    info = open_room(client)
    with ExitStack() as stack:
        sockets = everyone(client, stack, info)
        act(sockets, "authority", {"intent": "start_season"})
        for who in ["authority", "display", roles_of(info)[0]]:
            sockets[who].send_text(json.dumps({"intent": "timeout_vote", "season": 1}))
            assert sockets[who].receive_json()["type"] == "invalid", who
    assert phase(client, info["room"]) == "vote"


def test_a_room_restored_mid_vote_keeps_the_deadline_from_the_record(tmp_path: Path) -> None:
    clock = Clock()
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        info = open_room(client)
        with ExitStack() as stack:
            act(everyone(client, stack, info), "authority", {"intent": "start_season"})
        start = vote_opened(client, info["room"])
    clock.t = start + length(1) - 2 * TIMER_TICK_S  # test input: restarted shortly before the deadline
    with TestClient(create_app(settings(tmp_path), now=clock)) as client:
        assert phase(client, info["room"]) == "vote"
        # a countdown restarted at the restart would need the whole negotiation again; the record's needs two ticks
        clock.t += 2 * TIMER_TICK_S
        assert wait_for_phase(client, info["room"], PAST_VOTE) in PAST_VOTE
        assert chosen(client, info["room"])[-1]["payload"]["byTimeout"] is True
