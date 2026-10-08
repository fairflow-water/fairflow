# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Guards added after the correctness review of 2026-10-08 (docs/reviews/2026-10-08-correctness-review.md): each test
names the finding it closes. Inputs here are test inputs, not model values."""

import math
from dataclasses import replace

import numpy as np
import pytest
from test_engine_vs_blueprint import SCHEMES, SCORING
from test_scenario import REG, broken

from fairflow_engine import max_value, weighted_cea
from fairflow_engine.production import value_of
from fairflow_engine.scenario import load_scenario
from fairflow_engine.welfare import pwf_ede, welfare

FLOOR = SCORING.survivalFloor
SUPPLY = SCORING.welfareSupplyFloor


def identical(n=3):
    base = replace(SCHEMES[2], demandMm3=4.0, capacityT=2000.0, ky=1.0, price=1.0)
    return [replace(base, id=f"S{i}") for i in range(n)]


@pytest.mark.parametrize("estate", [1.0, 3.0, 7.0, 9.0, 12.0])
def test_e5_tied_farms_get_equal_adequacy_at_the_optimal_value(estate):
    farms = identical()
    Q = max_value(farms, estate, FLOOR)
    assert max(Q) - min(Q) <= 1e-6
    assert sum(Q) == pytest.approx(min(estate, 12.0), abs=1e-5)
    best = sum(value_of(s, q, FLOOR) for s, q in zip(farms, [estate / 3] * 3, strict=True))
    slope = max(s.capacityT / s.demandMm3 for s in farms)  # tolerance: n × 1e-6 Mm³ of rounding (§7.2) at the top slope
    assert sum(value_of(s, q, FLOOR) for s, q in zip(farms, Q, strict=True)) == pytest.approx(best, abs=3e-6 * slope)


def test_e5_untied_basin_is_unchanged():
    """The default basin has no shared marginal value, so the tie-break never runs there (§3.2 values stand)."""
    assert max_value(SCHEMES, 15.0, FLOOR) == max_value(list(reversed(SCHEMES)), 15.0, FLOOR)[::-1]


def test_e4_zero_weights_are_refused_and_zero_claims_need_none():
    with pytest.raises(ValueError, match="positive weight"):
        weighted_cea([3, 5], [0, 0], 6)
    assert weighted_cea([0, 5], [0, 1], 6) == [0.0, 5.0]


@pytest.mark.parametrize("gamma", [150.0, 400.0, 1e6])
def test_e6_large_gamma_approaches_the_minimum_without_underflow(gamma):
    shares = [SUPPLY, 1.0, 1.0]
    ede = pwf_ede(shares, gamma, SUPPLY)
    assert SUPPLY <= ede <= SUPPLY * 1.05


def test_e6_continuous_through_gamma_one():
    shares = [0.3, 0.7, 1.0]
    geometric = float(np.exp(np.log(shares).mean()))
    for g in (1 - 1e-12, 1 + 1e-12, 1 - 1e-6, 1 + 1e-6):
        assert pwf_ede(shares, g, SUPPLY) == pytest.approx(geometric, rel=1e-6)


def test_e6_welfare_refuses_an_infinite_gamma_and_agrees_with_the_ede():
    shares = [0.3, 0.7, 1.0]
    with pytest.raises(ValueError, match="finite"):
        welfare(SCHEMES, shares, math.inf, FLOOR, SUPPLY)
    assert welfare(SCHEMES, shares, 3, FLOOR, SUPPLY)["PWFede"] == pwf_ede(shares, 3, SUPPLY)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"basin__inflow__dryDrift": 0.5}, "dryDrift is not implemented"),
        ({"basin__aquifer__returnFlows": False}, "returnFlows = false is not implemented"),
        ({"basin__aquifer__surplusRecharge": False}, "surplusRecharge = false is not implemented"),
    ],
)
def test_e3_unimplemented_options_are_refused(change, message):
    load = load_scenario(broken(**change), REG)
    assert load.setup is None and any(message in e for e in load.errors)


@pytest.mark.parametrize(
    "change",
    [
        {"indicators": {"survivalFloor": 1}},
        {"indicators": {"survivalFloor": 0}},
        {"indicators": {"welfareSupplyFloor": 0}},
        {"indicators": {"r3Ramp": 0}},
        {"indicators": {"unknownKey": 1}},
    ],
)
def test_e7_degenerate_scoring_values_are_refused(change):
    load = load_scenario(broken(**change), REG)
    assert load.setup is None and any(e.startswith("schema:") for e in load.errors)


def test_e4_e7_scheme_weights_and_ky_are_bounded():
    for field, value in (("kappa", 0), ("ky", 2.5)):
        s = broken()
        s["schemes"][0][field] = value
        load = load_scenario(s, REG)
        assert load.setup is None and any(field in e for e in load.errors)


def test_e6_a_gamma_that_overflows_pwf_is_refused():
    load = load_scenario(broken(indicators={"welfareGamma": 1000}), REG)
    assert load.setup is None and any("overflows" in e for e in load.errors)
