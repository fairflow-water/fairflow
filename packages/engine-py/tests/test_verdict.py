# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""§2.7 verdict (review 2026-10-08, E1): with no pumping the water as used is the voted allocation, so the verdict must
name the voted lens, also when the table voted sufficientarian and chose how the floors are cut (ADR 0003), and when
another lens prescribes the same allocation."""

import pytest
from test_engine_vs_blueprint import LENSES, SCHEMES, SCORING, lens_params
from test_record import AUTHORITY, BASIN, INFLOW, ROLES, new_game

from fairflow_engine import allocate, verdict
from fairflow_engine.record import debrief_welfare
from fairflow_engine.welfare import pwf_ede

FLOOR = lens_params("sufficientarian").floor
SHORT = BASIN.reserve + 0.8 * sum(FLOOR * s.demandMm3 for s in SCHEMES)  # test input: the floors cannot all be met


@pytest.mark.parametrize("rule", ["proportional", "cea", "cel", "talmud", "capability"])
def test_no_pumping_names_the_voted_sufficientarian_lens_whatever_the_floor_rule(rule):
    g = new_game(inflow={card: SHORT for card in INFLOW})
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="sufficientarian")
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "floor_vote", rule=rule)
    g.submit(AUTHORITY, "close_floor_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    v = next(e for e in g.events if e["type"] == "season.resolved")["payload"]["sealed"]["verdict"]
    assert v == {"voted": "sufficientarian", "satisfied": "sufficientarian", "pumpingGap": 0.0}


def test_identical_ideal_allocations_name_the_voted_lens():
    """A proportional cut of the floors is the proportional allocation; the voted lens wins the tie, either way round."""
    estate = 0.8 * sum(FLOOR * s.demandMm3 for s in SCHEMES)
    lenses = [(lens, lens_params(lens)) for lens in LENSES]
    W = list(allocate("proportional", SCHEMES, estate, lens_params("proportional"), SCORING.survivalFloor).Q)
    for voted in ("sufficientarian", "proportional"):
        assert verdict(SCHEMES, estate, W, voted, 0.0, lenses, SCORING.survivalFloor)["satisfied"] == voted


def test_debrief_row_of_the_chosen_lens_uses_the_floor_rule_applied():
    g = new_game(inflow={card: SHORT for card in INFLOW})
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="sufficientarian")
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "floor_vote", rule="cel")
    g.submit(AUTHORITY, "close_floor_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    issued = next(e["payload"] for e in g.events if e["type"] == "allocation.issued")
    preview = next(p for p in g.events if p["type"] == "season.climate")["payload"]["previews"]
    whatever_works = next(p["Q"] for p in preview if p["lens"] == "sufficientarian")
    assert issued["Q"] != whatever_works  # the CEL cut differs from the proportional cut shown before the vote
    events = [*g.events, {"type": "debrief.opened", "season": 1, "payload": {"perPlayer": False}}]
    row = debrief_welfare(g.setup, events)["seasons"][0]["lenses"]["sufficientarian"]
    shares = [q / s.demandMm3 for q, s in zip(issued["Q"], SCHEMES, strict=True)]
    assert row[0] == pytest.approx(pwf_ede(shares, 0, g.setup.scoring.welfareSupplyFloor), abs=1e-6)
