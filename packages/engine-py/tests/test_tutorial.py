# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R3 season 0: a practice round in a normal year with two lenses, one private turn with pump cost 0 and no actions,
nothing scored; the game that follows is the same game it would have been without it."""

import pytest
from test_engine_vs_blueprint import BASIN
from test_record import ROLES, SEALED_KEYS, keys_in, new_game, play_game, play_season

from fairflow_engine import AUTHORITY, Rejection, audit, project, replay
from fairflow_engine.record import TUTORIAL_LENSES


def tutorial(g, lens="proportional", pumps=None):
    g.submit(AUTHORITY, "start_tutorial")
    g.submit(AUTHORITY, "propose", lens=lens)
    for role in ROLES:
        g.submit(role, "vote", lens=lens)
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=(pumps or {}).get(role, 0.0))
    return g


def resolved(g):
    return [e for e in g.events if e["type"] == "season.resolved"]


def test_tutorial_is_a_normal_year_with_two_lenses_and_free_pumping():
    g = new_game()
    g.submit(AUTHORITY, "start_tutorial")
    climate = g.events[-1]
    assert climate["season"] == 0 and climate["payload"]["tutorial"] is True
    assert climate["payload"]["card"] == "normal"
    assert climate["payload"]["inflow"] == g.setup.inflow["normal"]
    assert sorted(p["lens"] for p in climate["payload"]["previews"]) == sorted(TUTORIAL_LENSES)
    g.submit(AUTHORITY, "propose", lens="proportional")
    for role in ROLES:
        g.submit(role, "vote", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    turns = [e["payload"] for e in g.events if e["type"] == "private.opened"]
    assert {t["pumpCostPerMm3"] for t in turns} == {0}
    assert all(t["actions"] == {} for t in turns)


def test_nothing_in_the_tutorial_is_scored_or_carried():
    g = tutorial(new_game(), pumps={"A": BASIN.pump.cap})
    s = replay(g.events)
    assert s.phase == "reveal" and s.season == 0
    assert s.stock == g.setup.basin.aquifer.initial
    assert set(s.livelihood.values()) == {0} and s.scores == []
    assert s.previousLens is None
    done = next(e for e in g.events if e["type"] == "tutorial.resolved")
    assert done["payload"]["sealed"]["P"][0] == BASIN.pump.cap  # the practice pumping happened, at no cost
    assert done["payload"]["sealed"]["pumpCost"] == [0, 0, 0]


def test_the_game_after_a_tutorial_is_the_same_game():
    """Same nonce, same decisions: every season.resolved and game.ended payload is identical with or without season 0."""
    plain = play_game(new_game(3), pumps={"A": 1.0})
    practised = play_game(tutorial(new_game(3), lens="utilitarian", pumps={"B": 2.0}), pumps={"A": 1.0})
    assert [e["payload"] for e in resolved(practised)] == [e["payload"] for e in resolved(plain)]
    end = {e["type"]: e["payload"] for e in plain.events if e["type"] == "game.ended"}["game.ended"]
    end_p = {e["type"]: e["payload"] for e in practised.events if e["type"] == "game.ended"}["game.ended"]
    assert end_p == end
    assert audit(practised.setup, practised.events) == []


def test_tutorial_pumping_stays_private_like_any_season():
    g = tutorial(new_game(), pumps={"A": 1.0})
    public = [e for e in project(g.events, "public") if e["type"] == "tutorial.resolved"]
    assert public and not keys_in(public) & SEALED_KEYS
    mine = [e for e in project(g.events, "A") if e["type"] == "tutorial.resolved"]
    assert mine[0]["payload"]["self"]["P"] == 1.0


@pytest.mark.parametrize(
    ("step", "code"),
    [
        (lambda g: g.submit("A", "start_tutorial"), "not_authority"),
        (
            lambda g: (g.submit(AUTHORITY, "start_tutorial"), g.submit(AUTHORITY, "propose", lens="egalitarian")),
            "lens_not_in_tutorial",
        ),
        (lambda g: (play_season(g), g.submit(AUTHORITY, "start_tutorial")), "wrong_phase"),
    ],
)
def test_tutorial_rules(step, code):
    g = new_game()
    with pytest.raises(Rejection) as e:
        step(g)
    assert e.value.code == code


def test_no_actions_in_the_tutorial():
    g = new_game()
    g.submit(AUTHORITY, "start_tutorial")
    g.submit(AUTHORITY, "propose", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    with pytest.raises(Rejection) as e:
        g.submit("A", "commit", pumps=0.0, action="drip")
    assert e.value.code == "no_actions_in_tutorial"


def test_brief_and_length_ignore_the_tutorial():
    g = play_game(tutorial(new_game(), lens="utilitarian"))
    end = next(e["payload"] for e in g.events if e["type"] == "game.ended")
    assert end["seasonsPlayed"] == end["T"]
    assert len(end["brief"]["lensBySeason"]) == end["T"]
    assert "utilitarian" not in end["brief"]["lensBySeason"]
