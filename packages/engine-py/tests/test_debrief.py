# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""S9's welfare slider (ADR 0003): the engine computes PWF_γ's equally-distributed equivalent for every slider position;
the limiting cases are the mean and the minimum; the water as used appears only when per-player results are opened."""

import copy
from itertools import pairwise

import numpy as np
import pytest
from test_engine_vs_blueprint import BASIN, SCHEMES, SCORING
from test_record import new_game, play_game

from fairflow_engine import AUTHORITY, Rejection, audit, project, welfare
from fairflow_engine.record import debrief_welfare, slider_gammas
from fairflow_engine.welfare import pwf_ede

FLOOR = SCORING.welfareSupplyFloor
SHARES = [0.3, 0.7, 1.0]  # test input: shares of need


@pytest.mark.parametrize("gamma", [0.5, 2, 3, 7])
def test_ede_matches_the_welfare_function(gamma):
    want = welfare(SCHEMES, SHARES, gamma, SCORING.survivalFloor, FLOOR)["PWFede"]
    assert pwf_ede(SHARES, gamma, FLOOR) == pytest.approx(want, rel=1e-12)


def test_limiting_cases_are_mean_geometric_mean_and_minimum():
    s = np.maximum(FLOOR, np.minimum(SHARES, 1.0))
    assert pwf_ede(SHARES, 0, FLOOR) == pytest.approx(s.mean())
    assert pwf_ede(SHARES, 1, FLOOR) == pytest.approx(np.exp(np.log(s).mean()))
    assert pwf_ede(SHARES, float("inf"), FLOOR) == pytest.approx(s.min())


def test_slider_runs_from_zero_to_the_limit_and_starts_at_the_scenario_value():
    gammas, start = slider_gammas(SCORING.welfareGamma)
    assert gammas[0] == 0 and gammas[-1] is None
    assert gammas[start] == SCORING.welfareGamma
    finite = [g for g in gammas if g is not None]
    assert finite == sorted(finite)
    other, i = slider_gammas(2.5)  # a starting value that is not a grid position is added as one
    assert other[i] == 2.5


def finished(per_player):
    g = play_game(new_game(), pumps={"A": BASIN.pump.cap})
    g.submit(AUTHORITY, "open_debrief", perPlayer=per_player)
    return g


@pytest.mark.parametrize("per_player", [True, False])
def test_debrief_welfare_is_public_recomputable_and_monotone(per_player):
    g = finished(per_player)
    payload = next(e["payload"] for e in project(g.events, "public") if e["type"] == "debrief.welfare")
    seasons = [e["season"] for e in g.events if e["type"] == "season.resolved"]
    assert [x["season"] for x in payload["seasons"]] == seasons
    for x in payload["seasons"]:
        assert ("used" in x) is per_player  # ADR 0004: as-used welfare would reveal pumping
        for row in [*x["lenses"].values(), *([x["used"]] if per_player else [])]:
            assert len(row) == len(payload["gammas"])
            assert all(a >= b - 1e-6 for a, b in pairwise(row))  # power means fall as γ rises
    assert audit(g.setup, g.events) == []


def test_tampered_debrief_welfare_is_detected():
    g = finished(True)
    events = copy.deepcopy(g.events)
    w = next(e for e in events if e["type"] == "debrief.welfare")
    w["payload"]["start"] += 1
    assert "debrief.welfare does not recompute from the record" in audit(g.setup, events)
    assert debrief_welfare(g.setup, g.events[:-1])["start"] != w["payload"]["start"]


def test_review_answers_stay_with_their_author_even_after_a_per_player_debrief():
    g = finished(True)
    g.submit("A", "review_answer", part=1, item="like.1", value="the vote made us talk")
    g.submit("A", "review_answer", part=1, item="like.1", value="revised")
    assert [e["payload"]["value"] for e in project(g.events, "A") if e["type"] == "review.answer"] == [
        "the vote made us talk",
        "revised",
    ]
    for viewer in ("public", "B", AUTHORITY):
        assert not [e for e in project(g.events, viewer) if e["type"] == "review.answer"]
    assert audit(g.setup, g.events) == []


@pytest.mark.parametrize(
    ("actor", "args", "code"),
    [
        (AUTHORITY, {"part": 1, "item": "like.1", "value": "x"}, "not_a_player"),
        ("A", {"part": 4, "item": "like.1", "value": "x"}, "bad_input"),
        ("A", {"part": 1, "item": "Not an id!", "value": "x"}, "bad_input"),
        ("A", {"part": 1, "item": "like.1", "value": 7}, "bad_input"),
    ],
)
def test_review_answers_are_validated(actor, args, code):
    g = finished(False)
    before = len(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(actor, "review_answer", **args)
    assert e.value.code == code
    assert len(g.events) == before


def test_review_waits_for_the_end_of_the_game():
    g = new_game()
    with pytest.raises(Rejection) as e:
        g.submit("A", "review_answer", part=1, item="like.1", value="x")
    assert e.value.code in ("wrong_phase",)
