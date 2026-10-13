# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0013: the server's private-turn deadline. The engine commits an untouched phone's choice for every scheme that
has not committed, marks which side's timer fired, and keeps that mark out of every projection until a per-player
debrief."""

import copy
import json

import pytest
from test_record import REGISTRY, ROLES, SCENARIO, keys_in, new_game, play_season
from test_tutorial import tutorial

from fairflow_engine import AUTHORITY, ENGINE, Rejection, audit, project, replay, verify_reveal
from fairflow_engine.record import AUTO_COMMIT_FIELDS
from fairflow_engine.scenario import load_scenario


def open_private(g, start="start_season"):
    """Open a season (or the practice round) up to its private turns."""
    g.submit(AUTHORITY, start)
    g.submit(AUTHORITY, "propose", lens="proportional")
    for role in ROLES:
        g.submit(role, "vote", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    assert replay(g.events).phase == "private"
    return g


def offered(g, role):
    return next(
        e["payload"]
        for e in reversed(g.events)
        if e["type"] == "private.opened" and e["payload"]["role"] == role and e["season"] == replay(g.events).season
    )


def plays(g, season):
    return {e["payload"]["role"]: e for e in g.events if e["type"] == "action.played" and e["season"] == season}


def test_server_timeout_commits_the_untouched_default_and_resolves():
    g = open_private(new_game())
    season = replay(g.events).season
    first = {r: offered(g, r)["options"][0]["pumps"] for r in ROLES}
    g.submit("A", "commit", pumps=1.0, action="expand")
    g.submit(ENGINE, "timeout_private", season=season)
    played = plays(g, season)
    assert played["A"]["payload"] == {k: v for k, v in played["A"]["payload"].items() if k not in AUTO_COMMIT_FIELDS}
    for r in ROLES[1:]:
        p = played[r]["payload"]
        assert played[r]["actor"] == r and played[r]["visibility"] == "sealed"
        assert p["pumps"] == first[r] == 0  # R10 "0..cap": the first offered level is 0 pumps
        assert p["action"] is None and p["autoCommitted"] is True and p["autoCommittedBy"] == "server"
    assert replay(g.events).phase in ("reveal", "ended")
    assert audit(g.setup, g.events) == []


def test_a_timed_out_season_resolves_exactly_as_the_same_commits_made_by_hand():
    timed = open_private(new_game())
    by_hand = open_private(new_game())
    season = replay(timed.events).season
    timed.submit("A", "commit", pumps=1.0)
    by_hand.submit("A", "commit", pumps=1.0)
    timed.submit(ENGINE, "timeout_private", season=season)
    for r in ROLES[1:]:
        by_hand.submit(r, "commit", pumps=offered(by_hand, r)["options"][0]["pumps"])
    a = next(e for e in timed.events if e["type"] == "season.resolved")
    b = next(e for e in by_hand.events if e["type"] == "season.resolved")
    assert a["payload"] == b["payload"]


@pytest.mark.parametrize("actor", ["A", AUTHORITY, "display", "public"])
def test_only_the_engine_host_can_time_out_a_turn(actor):
    g = open_private(new_game())
    before = copy.deepcopy(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(actor, "timeout_private", season=replay(g.events).season)
    assert e.value.code == "not_engine" and g.events == before


def test_a_timer_from_another_season_or_phase_is_refused():
    g = new_game()
    with pytest.raises(Rejection) as e:
        g.submit(ENGINE, "timeout_private", season=0)  # lobby
    assert e.value.code == "wrong_phase"
    play_season(g)
    open_private(g)
    before = copy.deepcopy(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(ENGINE, "timeout_private", season=replay(g.events).season - 1)  # left over from the last season
    assert e.value.code == "stale_timer" and g.events == before


def test_the_phone_timer_is_recorded_as_the_phone():
    g = open_private(new_game())
    season = replay(g.events).season
    g.submit("A", "commit", pumps=1.0, autoCommitted=True)
    g.submit("B", "commit", pumps=0.0, autoCommitted=False)
    p = plays(g, season)
    assert p["A"]["payload"]["autoCommitted"] is True and p["A"]["payload"]["autoCommittedBy"] == "phone"
    assert not set(AUTO_COMMIT_FIELDS) & set(p["B"]["payload"])
    with pytest.raises(Rejection) as e:
        g.submit("C", "commit", pumps=0.0, autoCommitted="yes")
    assert e.value.code == "bad_input"


def test_the_practice_round_times_out_too():
    g = open_private(new_game(), start="start_tutorial")
    g.submit("A", "commit", pumps=1.0)
    g.submit(ENGINE, "timeout_private", season=0)
    assert any(e["type"] == "tutorial.resolved" for e in g.events)
    fired = {r: e["payload"].get("autoCommittedBy") for r, e in plays(g, 0).items()}
    assert fired == {"A": None, "B": "server", "C": "server"}
    assert audit(g.setup, g.events) == []


def test_a_timebox_ends_the_game_when_a_seat_is_absent():
    """R20 stands: the time-box ends play after the current season, which now always resolves."""
    g = new_game()
    play_season(g)
    open_private(g)
    g.submit(AUTHORITY, "timebox", sessionMinute=80)
    g.submit("A", "commit", pumps=0.0)
    g.submit("B", "commit", pumps=0.0)
    assert replay(g.events).phase == "private"  # C's phone is gone
    g.submit(ENGINE, "timeout_private", season=replay(g.events).season)
    ended = next(e for e in g.events if e["type"] == "game.ended")
    assert ended["payload"]["truncated"] and verify_reveal(g.events[0], ended) and audit(g.setup, g.events) == []


def timed_game():
    """A game with a phone timeout and a server timeout in its first season and a practice round before it."""
    g = tutorial(new_game())
    open_private(g)
    season = replay(g.events).season
    g.submit("A", "commit", pumps=1.0, autoCommitted=True)
    g.submit(ENGINE, "timeout_private", season=season)
    return g


VIEWERS = ["public", AUTHORITY, *ROLES]
VOTE_TIMERS = ("lens.chosen", "lens.floorRule")  # R8: these public events have always said whether a vote timed out


def marks(events) -> set:
    """Timeout marks anywhere except the vote timer's own public byTimeout."""
    return set(AUTO_COMMIT_FIELDS) & keys_in([e for e in events if e["type"] not in VOTE_TIMERS])


def test_the_timeout_marks_reach_no_projection_before_a_per_player_debrief():
    """ADR 0013 and ADR 0004: a server timeout implies 0 pumps, so no screen — not even the scheme's own — learns that a
    timer fired until the debrief opens per player; a totals-only debrief never shows it."""
    g = timed_game()
    while replay(g.events).phase != "ended":
        play_season(g)
    assert set(AUTO_COMMIT_FIELDS) <= marks(g.events)  # the record keeps them
    for viewer in VIEWERS:
        seen = project(g.events, viewer)
        assert not marks(seen), viewer
        assert "autoCommittedBy" not in json.dumps(seen), viewer
    totals = copy.deepcopy(g)
    totals.submit(AUTHORITY, "open_debrief", perPlayer=False)
    for viewer in VIEWERS:
        assert not marks(project(totals.events, viewer)), viewer
    g.submit(AUTHORITY, "open_debrief", perPlayer=True)
    for viewer in VIEWERS:
        fired = [e["payload"].get("autoCommittedBy") for e in project(g.events, viewer) if e["type"] == "action.played"]
        assert fired.count("phone") == 1 and fired.count("server") == 2, viewer


def test_a_scheme_still_sees_its_own_commit_without_the_mark():
    g = timed_game()
    season = replay(g.events).season
    for role in ROLES:
        own = [e for e in project(g.events, role) if e["type"] == "action.played" and e["season"] == season]
        assert len(own) == 1 and own[0]["payload"]["role"] == role
        assert set(own[0]["payload"]) == {"role", "pumps", "action", "committedAt"}


@pytest.mark.parametrize("reserved", ["authority", "engine"])
def test_scheme_ids_cannot_take_a_reserved_role(reserved):
    scenario = copy.deepcopy(SCENARIO)
    scenario["schemes"][0]["id"] = reserved
    load = load_scenario(scenario, REGISTRY)
    assert load.setup is None and any("reserved" in e for e in load.errors)
