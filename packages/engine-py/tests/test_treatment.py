# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R1 and ADR 0018 decision 3: every game records `treatment.assigned` before season 1, public, with who assigned it.
In room mode the facilitator sets the arms at room creation; the scenario's `treatments` block gives the defaults. Only
the Authority hand-over season is built for the class (2026-11-18); the other arms stay off, so a record never claims
an arm the game did not play. A scenario without the block records the control: every arm off, no hand-over."""

import copy
from dataclasses import replace

import pytest
from test_record import REGISTRY, SCENARIO, clock, new_game, nonce, play_season, setup

from fairflow_engine import Game, Rejection, audit, project, replay
from fairflow_engine.scenario import load_scenario

ARMS = SCENARIO["treatments"]
FIELDS = {"silentMode", "universalisationNudge", "secretBallot", "authorityHandoverSeason", "deliberation", "assignedBy"}


def loaded():
    load = load_scenario(SCENARIO, REGISTRY)
    assert load.setup is not None, load.errors
    return load.setup


def create(s=None, **kw) -> Game:
    return Game.create(s or loaded(), "t0", "room", {"appVersion": "test"}, clock(), nonce(0), **kw)


def assigned(g: Game) -> dict:
    [e] = [e for e in g.events if e["type"] == "treatment.assigned"]
    return e


def test_every_game_records_its_arms_right_after_creation_and_before_season_1():
    g = create()
    e = assigned(g)
    assert [x["type"] for x in g.events] == ["game.created", "treatment.assigned"]
    assert (e["actor"], e["visibility"], e["season"]) == ("engine", "public", 0)
    assert set(e["payload"]) == FIELDS  # the §6.2 fields; randomisationSeed only once assignment is random
    assert e["payload"]["assignedBy"] == "facilitator"
    assert e["payload"]["deliberation"] == SCENARIO["session"]["deliberation"]
    for arm, value in ARMS.items():
        assert e["payload"][arm] == value  # the scenario's defaults


def test_the_facilitator_sets_the_hand_over_season_and_0_means_never():
    _, last = loaded().gameLength
    for season in (0, last - 1):
        assert assigned(create(authorityHandoverSeason=season))["payload"]["authorityHandoverSeason"] == season


@pytest.mark.parametrize("season", [-1, "loaded-max", True, 1.5])
def test_a_hand_over_season_outside_the_game_is_refused(season):
    s = loaded()
    value = s.gameLength[1] if season == "loaded-max" else season  # after the longest game's last season: never reached
    with pytest.raises(Rejection) as e:
        create(s, authorityHandoverSeason=value)
    assert e.value.code == "bad_treatment"


def test_a_setup_without_arms_records_the_control():
    payload = assigned(create(setup()))["payload"]
    assert payload == {
        "silentMode": False,
        "universalisationNudge": False,
        "secretBallot": False,
        "authorityHandoverSeason": 0,
        "deliberation": None,  # no scenario session to read it from
        "assignedBy": "facilitator",
    }


def test_everyone_sees_the_arms_and_the_record_still_audits():
    g = new_game()
    play_season(g)
    for viewer in ["public", "authority", g.setup.schemes[0].id]:
        assert any(e["type"] == "treatment.assigned" for e in project(g.events, viewer))
    assert replay(g.events).handoverSeason == 0
    assert audit(g.setup, g.events) == []


def test_the_state_carries_the_hand_over_season():
    assert replay(create(authorityHandoverSeason=2).events).handoverSeason == 2


@pytest.mark.parametrize("arm", ["silentMode", "universalisationNudge", "secretBallot"])
def test_a_scenario_cannot_switch_on_an_arm_that_is_not_built(arm):
    scenario = copy.deepcopy(SCENARIO)
    scenario["treatments"][arm] = True
    load = load_scenario(scenario, REGISTRY)
    assert load.setup is None and any(arm in err for err in load.errors)


def test_a_scenario_hand_over_season_must_fall_inside_the_game():
    scenario = copy.deepcopy(SCENARIO)
    scenario["treatments"]["authorityHandoverSeason"] = scenario["basin"]["gameLength"]["max"]
    load = load_scenario(scenario, REGISTRY)
    assert load.setup is None and any("authorityHandoverSeason" in err for err in load.errors)


def test_an_unknown_arm_is_a_schema_error():
    scenario = copy.deepcopy(SCENARIO)
    scenario["treatments"]["surprise"] = False
    assert load_scenario(scenario, REGISTRY).setup is None


def test_the_arms_change_no_basin_result():
    """The hand-over season is a room setting: two games from one nonce, with different arms, play identically."""
    a, b = create(authorityHandoverSeason=0), create(authorityHandoverSeason=2)
    strip = [{k: v for k, v in e.items() if k != "t"} for e in a.events if e["type"] != "treatment.assigned"]
    assert strip == [{k: v for k, v in e.items() if k != "t"} for e in b.events if e["type"] != "treatment.assigned"]
    assert replace(a.secrets) == b.secrets
