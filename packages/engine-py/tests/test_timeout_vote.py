# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R8, R20 (ADR 0014): the server's negotiation deadline. At expiry a single plurality leader is chosen; with no
proposal, no vote or a tie, the previous season's lens applies (the scenario's default in season 1). `lens.chosen`
records byTimeout either way."""

import copy

import pytest
from test_record import REGISTRY, ROLES, SCENARIO, new_game, play_season
from test_tutorial import tutorial

from fairflow_engine import AUTHORITY, ENGINE, Rejection, audit, replay
from fairflow_engine.scenario import load_scenario


def chosen(g):
    return [e for e in g.events if e["type"] == "lens.chosen"][-1]


def expire(g):
    g.submit(ENGINE, "timeout_vote", season=replay(g.events).season)
    return chosen(g)


def test_no_proposal_in_season_1_applies_the_scenario_default():
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    c = expire(g)
    assert (c["actor"], c["payload"]["lens"], c["payload"]["byTimeout"]) == ("engine", g.setup.defaultLens, True)
    assert replay(g.events).phase == "private"


def test_no_proposal_later_applies_the_previous_season_lens():
    g = new_game()
    play_season(g, lenses=("egalitarian",))
    g.submit(AUTHORITY, "start_season")
    assert expire(g)["payload"]["lens"] == "egalitarian"


def test_after_the_practice_round_season_1_still_falls_back_to_the_default():
    g = tutorial(new_game(), lens="utilitarian")
    g.submit(AUTHORITY, "start_season")
    assert expire(g)["payload"]["lens"] == g.setup.defaultLens


def test_a_single_leader_at_expiry_is_chosen_with_its_tally():
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    for lens in ("egalitarian", "capability"):
        g.submit(AUTHORITY, "propose", lens=lens)
    g.submit("A", "vote", lens="capability")
    g.submit("B", "vote", lens="capability")
    g.submit("C", "vote", lens="egalitarian")
    p = expire(g)["payload"]
    assert (p["lens"], p["tally"], p["byTimeout"], p["tieBreak"]) == (
        "capability",
        {"capability": 2, "egalitarian": 1},
        True,
        False,
    )


@pytest.mark.parametrize("votes", [{}, {"A": "egalitarian", "B": "capability"}])
def test_no_vote_or_a_tie_at_expiry_applies_the_previous_lens(votes):
    g = new_game()
    play_season(g, lenses=("talmud",))
    g.submit(AUTHORITY, "start_season")
    for lens in ("egalitarian", "capability"):
        g.submit(AUTHORITY, "propose", lens=lens)
    for role, lens in votes.items():
        g.submit(role, "vote", lens=lens)
    p = expire(g)["payload"]
    assert (p["lens"], p["byTimeout"], p["tally"]) == ("talmud", True, {lens: 1 for lens in votes.values()})
    assert replay(g.events).phase == "private"


def test_the_practice_round_times_out_too():
    g = new_game()
    g.submit(AUTHORITY, "start_tutorial")
    g.submit(AUTHORITY, "propose", lens="utilitarian")
    g.submit("A", "vote", lens="utilitarian")
    assert expire(g)["payload"]["lens"] == "utilitarian"
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    assert any(e["type"] == "tutorial.resolved" for e in g.events)


@pytest.mark.parametrize(
    "actor,season_shift,phase,code",
    [
        ("authority", 0, "vote", "not_engine"),
        ("A", 0, "vote", "not_engine"),
        (ENGINE, -1, "vote", "stale_timer"),  # a timer left from the last season
        (ENGINE, 0, "private", "wrong_phase"),  # the Authority closed the vote in time
    ],
)
def test_who_and_when(actor, season_shift, phase, code):
    g = new_game()
    play_season(g)
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="proportional")
    if phase == "private":
        g.submit(AUTHORITY, "close_vote")
    before = list(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(actor, "timeout_vote", season=replay(g.events).season + season_shift)
    assert e.value.code == code
    assert g.events == before


def test_a_timed_out_vote_audits_and_the_game_goes_on():
    g = new_game()
    for _ in range(2):
        g.submit(AUTHORITY, "start_season")
        expire(g)
        for role in ROLES:
            g.submit(role, "commit", pumps=0.0)
    assert audit(g.setup, g.events) == []


@pytest.mark.parametrize(
    "negotiation", [{"seasons0to2": 180}, {"seasons0to2": 0, "from3": 240}, {"seasons0to2": "3:00", "from3": 240}, 180]
)
def test_a_scenario_with_an_unusable_negotiation_time_does_not_load(negotiation):
    """The server and the bar compute the deadline from both lengths; a missing, zero or non-numeric one is refused."""
    scenario = copy.deepcopy(SCENARIO)
    scenario["session"]["negotiationS"] = negotiation
    load = load_scenario(scenario, REGISTRY)
    assert load.setup is None and any("negotiationS" in e for e in load.errors)


def test_a_scenario_without_a_negotiation_time_loads_and_has_no_timer():
    scenario = copy.deepcopy(SCENARIO)
    del scenario["session"]["negotiationS"]
    assert load_scenario(scenario, REGISTRY).setup is not None
