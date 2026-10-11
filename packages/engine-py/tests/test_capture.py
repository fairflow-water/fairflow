# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0009: with the baseflow coupling the river and the aquifer are one balance. Natural recharge is balanced at full
storage by discharge the climate cards already contain; below full, the aquifer gains exactly the baseflow the river
loses (capture), never both. Stocks, inflows and pumping are test inputs drawn by Hypothesis."""

from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_engine_vs_blueprint import FULL

from fairflow_engine import inflow_loss_next, natural_gain, resolve_season
from fairflow_engine.aquifer import pump_cap

BASIN = FULL.basin
Q = BASIN.aquifer


@given(stock=st.floats(Q.reserve, Q.initial))
def test_the_aquifer_gains_what_the_river_loses(stock):
    """The loss applied to the next season's inflow at a level equals the aquifer's natural gain at that level."""
    assert natural_gain(BASIN, stock) == inflow_loss_next(BASIN, stock)
    assert 0 <= natural_gain(BASIN, stock) <= Q.naturalRecharge


def test_a_full_aquifer_gains_nothing_naturally_and_the_river_loses_nothing():
    assert natural_gain(BASIN, Q.initial) == 0 == inflow_loss_next(BASIN, Q.initial)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    stock=st.floats(Q.reserve, Q.initial),
    card=st.sampled_from(["wet", "normal", "dry"]),
    share=st.lists(st.floats(0, 1), min_size=3, max_size=3),
    lens=st.sampled_from(["proportional", "utilitarian", "egalitarian", "capability", "sufficientarian"]),
)
def test_the_basin_balance_closes_with_capture(stock, card, share, lens):
    """AW + G − (Σ βW + (1 − ρ) Σ(1 − β)W) = ΔB + spill, G the natural gain, and S > 1 exactly when storage falls."""
    pumps = [s * pump_cap(BASIN, stock, x) for s, x in zip(share, FULL.schemes, strict=True)]
    loss = inflow_loss_next(BASIN, stock)
    r = resolve_season(
        FULL.schemes, BASIN, FULL.inflow[card] - loss, stock, lens, dict(FULL.lenses)[lens], pumps, FULL.scoring
    )
    beta = [x.beta for x in FULL.schemes]
    draw = sum(b * w for b, w in zip(beta, r["W"], strict=True)) + (1 - Q.returnRecharge) * sum(
        (1 - b) * w for b, w in zip(beta, r["W"], strict=True)
    )
    lhs = r["allocable"] + natural_gain(BASIN, stock) - draw
    assert abs(lhs - (r["stockNext"] - stock + r["spill"])) <= 1e-5  # tolerance: outputs rounded to 1e-6 (§7.2)
    if abs(r["stockNext"] - stock) > 1e-5:
        assert (r["S"] > 1) == (r["stockNext"] < stock)


def test_without_coupling_the_v1_rule_credits_all_of_r0():
    v1 = replace(BASIN, aquifer=replace(Q, baseflowLossPerMm3=None))
    assert natural_gain(v1, Q.reserve) == Q.naturalRecharge
