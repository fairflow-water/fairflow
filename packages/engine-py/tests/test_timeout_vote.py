# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R8, R20 (ADR 0014): the server's negotiation deadline. At expiry the previous season's lens applies (the scenario's
default in season 1), whatever was proposed or voted: section 13 row 9, "previous lens everywhere". A lens is chosen
only by close_vote. `lens.chosen` records byTimeout. After a veto, a vetoed previous lens gives way to the default
(ADR 0015)."""

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


@pytest.mark.parametrize(
    "proposals,votes",
    [
        (("egalitarian", "capability"), {"A": "capability", "B": "capability", "C": "egalitarian"}),  # a single leader
        (("egalitarian", "capability"), {"A": "egalitarian", "B": "capability"}),  # a tie
        (("egalitarian", "capability"), {}),  # proposals and no vote
        (("egalitarian",), {}),  # one proposal, no vote: close_vote would take it, expiry does not
    ],
)
def test_expiry_applies_the_previous_lens_whatever_was_proposed_or_voted(proposals, votes):
    """Section 13 row 9, "previous lens everywhere": a lens is chosen only by close_vote; the votes cast are recorded."""
    g = new_game()
    play_season(g, lenses=("talmud",))
    g.submit(AUTHORITY, "start_season")
    for lens in proposals:
        g.submit(AUTHORITY, "propose", lens=lens)
    for role, lens in votes.items():
        g.submit(role, "vote", lens=lens)
    p = expire(g)["payload"]
    tally = {lens: list(votes.values()).count(lens) for lens in set(votes.values())}
    assert (p["lens"], p["byTimeout"], p["tieBreak"], p["tally"]) == ("talmud", True, False, tally)
    assert replay(g.events).phase == "private"


def veto_then_expire(previous: str, proposals: tuple[str, ...], vetoed: str):
    g = new_game()
    play_season(g, lenses=(previous,))
    g.submit(AUTHORITY, "start_season")
    for lens in proposals:
        g.submit(AUTHORITY, "propose", lens=lens)
    g.submit(AUTHORITY, "veto", lens=vetoed)
    return g, expire(g)["payload"]


def test_expiry_during_a_veto_re_vote_skips_a_vetoed_previous_lens_for_the_scenario_default():
    """ADR 0015 addition to R8 (accepted by the maintainer, 2026-10-15): when the re-vote after a veto runs out of time
    and the previous lens is the one vetoed, the scenario's default lens applies instead; `lens.chosen` names the veto."""
    g, p = veto_then_expire("egalitarian", ("egalitarian", "capability"), "egalitarian")
    assert g.setup.defaultLens != "egalitarian"  # test input: the scenario's default is not the vetoed lens
    assert (p["lens"], p["byTimeout"], p["tally"], p["veto"], p["revote"]) == (
        g.setup.defaultLens,
        True,
        {},
        "egalitarian",
        True,
    )


def test_expiry_after_a_veto_of_another_lens_still_applies_the_previous_lens():
    """Only a vetoed previous lens is skipped: a veto of some other proposal leaves section 13 row 9 as it was."""
    _, p = veto_then_expire("egalitarian", ("capability", "talmud"), "capability")
    assert (p["lens"], p["veto"]) == ("egalitarian", "capability")


def test_expiry_when_the_vetoed_lens_is_the_default_itself_applies_the_default():
    """Pinned as built, an open question for the maintainer: the decision names the default as the fallback, so a
    vetoed default lens still applies when the re-vote runs out of time."""
    g0 = new_game()
    default = g0.setup.defaultLens
    other = next(lens for lens in ("egalitarian", "capability") if lens != default)  # test input
    _, p = veto_then_expire(default, (default, other), default)
    assert (p["lens"], p["veto"]) == (default, default)


def test_the_practice_round_times_out_too():
    g = new_game()
    g.submit(AUTHORITY, "start_tutorial")
    g.submit(AUTHORITY, "propose", lens="utilitarian")
    g.submit("A", "vote", lens="utilitarian")
    assert expire(g)["payload"]["lens"] == g.setup.defaultLens  # no season precedes it: the scenario's default
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


def test_a_negotiation_time_given_as_true_does_not_load():
    """JSON true is a number to Python (bool is an int subclass); a length of `true` seconds is refused like any
    other non-number."""
    scenario = copy.deepcopy(SCENARIO)
    scenario["session"]["negotiationS"] = {**scenario["session"]["negotiationS"], "seasons0to2": True}
    load = load_scenario(scenario, REGISTRY)
    assert load.setup is None and any("negotiationS" in e for e in load.errors)


def test_a_scenario_without_a_negotiation_time_loads_and_has_no_timer():
    scenario = copy.deepcopy(SCENARIO)
    del scenario["session"]["negotiationS"]
    assert load_scenario(scenario, REGISTRY).setup is not None
