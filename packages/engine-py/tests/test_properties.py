# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Blueprint §9.1 properties on seeded random basins. The basins are random draws, not model values."""

from dataclasses import replace

import numpy as np
import pytest

from fairflow_engine import FLOOR_RULES, Basin, LensParams, Scheme, Scoring, allocate, resolve_season, value_of
from test_engine_vs_blueprint import BASIN, LENSES, SCORING, lens_params

RNG = np.random.default_rng(20261005)


def random_schemes(rng, beta=None, uniform_depth=False):
    n = int(rng.integers(3, 6))
    out = []
    for i in range(n):
        D = float(rng.uniform(1, 10))
        out.append(Scheme(id=str(i), name=str(i), seat=i + 1, demandMm3=D, capacityT=float(rng.uniform(500, 5500)),
                          ky=float(rng.uniform(0.5, 1.3)), beta=float(rng.uniform(0.5, 1)) if beta is None else beta,
                          people=float(rng.uniform(10, 2000)), kappa=1.0, price=float(rng.uniform(0.5, 1.5)),
                          areaHa=D * 100 if uniform_depth else float(rng.uniform(100, 1000))))
    return out


def params_for(lens, floor_scaling):
    """Registry parameters, with each ADR 0003 floor rule the table can choose."""
    p = lens_params(lens)
    return replace(p, floorScaling=floor_scaling) if lens == "sufficientarian" else p


def max_slope(schemes):
    """Largest marginal value per Mm³ of any scheme, read off the production function (bounds the effect of rounding)."""
    f = SCORING.survivalFloor
    out = 0.0
    for x in schemes:
        L, D = f * x.demandMm3, x.demandMm3
        out = max(out, value_of(x, L, f) / L, (value_of(x, D, f) - value_of(x, L, f)) / (D - L))
    return out


@pytest.mark.parametrize("floor_scaling", sorted(FLOOR_RULES))
def test_allocations_sum_and_bounds(floor_scaling):
    """Σ Q = min(AW, ΣD); 0 ≤ Q_i ≤ D_i (rounded to 1e-6, §7.2)."""
    for _ in range(150):
        s = random_schemes(RNG)
        D = np.array([x.demandMm3 for x in s])
        AW = float(RNG.uniform(0, 1.2)) * D.sum()
        for lens in LENSES:
            Q = np.array(allocate(lens, s, AW, params_for(lens, floor_scaling), SCORING.survivalFloor).Q)
            assert abs(Q.sum() - min(AW, D.sum())) <= 1e-5
            assert (Q >= 0).all() and (Q <= D + 1e-6).all()


def test_utilitarian_is_never_beaten_by_random_feasible_allocations():
    """§9.1: the maximiser is never beaten by 10,000 random feasible allocations."""
    for _ in range(10):
        s = random_schemes(RNG)
        D = np.array([x.demandMm3 for x in s])
        AW = float(RNG.uniform(0, 1)) * D.sum()
        Q = allocate("utilitarian", s, AW, LensParams(), SCORING.survivalFloor).Q
        best = sum(value_of(x, q, SCORING.survivalFloor) for x, q in zip(s, Q))
        rounding = len(s) * 0.5e-6 * max_slope(s)  # Q is rounded to 1e-6 at the event boundary (§7.2)
        for _ in range(1000):
            w = RNG.dirichlet(np.ones(len(s)))
            q = np.minimum(D, w * AW)
            for _ in range(len(s)):  # redistribute what capped schemes could not take
                room = D - q
                left = AW - q.sum()
                if left <= 1e-12 or room.sum() <= 0:
                    break
                q = q + room / room.sum() * min(left, room.sum())
            assert sum(value_of(x, v, SCORING.survivalFloor) for x, v in zip(s, q)) <= best + rounding


def test_identities():
    """§9.1: F = 1 at full demand; E_PJ = 1 for proportional; per-hectare E_SE = E_PJ in uniform-depth basins;
    E_SE(claimant) = 1 for equal shares when uncapped."""
    for _ in range(100):
        s = random_schemes(RNG, uniform_depth=True)
        D = np.array([x.demandMm3 for x in s])
        full = resolve_season(s, BASIN, BASIN.reserve + D.sum() * 1.5, 20, "egalitarian", LensParams(), [0] * len(s), SCORING)
        assert full["F"]["consumed"] == pytest.approx(1, abs=1e-6) and full["F"]["diverted"] == pytest.approx(1, abs=1e-6)
        part = resolve_season(s, BASIN, BASIN.reserve + float(RNG.uniform(0, 1)) * D.sum(), 20, "proportional",
                              LensParams(), [0] * len(s), SCORING)
        tol = 1e-6 / min(part["W"])  # relative effect of rounding the smallest share to 1e-6
        assert part["ePJ"] == pytest.approx(1, abs=tol)
        assert part["eSE"]["hectare"] == pytest.approx(part["ePJ"], abs=tol)
        eq = resolve_season(s, BASIN, BASIN.reserve + D.min() * len(s) * float(RNG.uniform(0, 1)), 20, "egalitarian",
                            LensParams(), [0] * len(s), SCORING)
        assert eq["eSE"]["claimant"] == pytest.approx(1, abs=1e-6 / min(eq["W"]))


@pytest.mark.parametrize("floor_scaling", sorted(FLOOR_RULES))
def test_aquifer_mass_balance(floor_scaling):
    """§9.1: the aquifer balance closes to 1e-6 every season."""
    for i in range(200):
        s = random_schemes(RNG)
        r0 = float(RNG.uniform(0, 2))
        basin = replace(BASIN, aquifer=replace(BASIN.aquifer, naturalRecharge=r0))
        D = sum(x.demandMm3 for x in s)
        stock = float(RNG.uniform(5, 25))
        r = resolve_season(s, basin, basin.reserve + float(RNG.uniform(0, 1.3)) * D, stock, LENSES[i % len(LENSES)],
                           params_for(LENSES[i % len(LENSES)], floor_scaling), list(RNG.uniform(0, 2, len(s))), SCORING)
        balance = stock + r["allocation"]["surplusToAquifer"] + r0 + r["returnFlow"] - r["pumpsTotal"]
        assert abs(r["stockNext"] - max(basin.aquifer.reserve, balance)) <= 1e-5
        assert r["pumpsTotal"] <= max(0.0, stock - basin.aquifer.reserve) + 1e-6


def search_s_vs_pumping(beta):
    """Count seasons with no surplus where (S > 1) disagrees with (ΣP > r₀)."""
    rng = np.random.default_rng(7)
    disagree = 0
    for _ in range(400):
        s = random_schemes(rng, beta=beta)
        r0 = float(rng.uniform(0, 2))
        basin = replace(BASIN, aquifer=replace(BASIN.aquifer, naturalRecharge=r0, reserve=0.0))
        D = sum(x.demandMm3 for x in s)
        r = resolve_season(s, basin, basin.reserve + float(rng.uniform(0.2, 1)) * D, 50, "proportional", LensParams(),
                           list(rng.uniform(0, 2, len(s))), SCORING)
        if abs(r["pumpsTotal"] - r0) > 1e-4 and (r["S"] > 1) != (r["pumpsTotal"] > r0):
            disagree += 1
    return disagree


def test_s_exceeds_one_iff_pumping_exceeds_recharge_at_beta_one():
    """§9.1 'S > 1 iff ΣP > r₀ in a season with no surplus' — holds with β = 1 (no counterexample in 400 seasons)."""
    assert search_s_vs_pumping(beta=1.0) == 0


def test_s_property_with_beta_below_one_is_reported():
    """With β < 1 the §9.1 statement has counterexamples; this records the finding for the science reviewer."""
    assert search_s_vs_pumping(beta=0.75) > 0


@pytest.mark.parametrize("rule", sorted(FLOOR_RULES))
def test_floor_shortfall_rules(rule):
    """ADR 0003: when the floors exceed AW, the chosen §2.3 rule cuts them: Σ Q = AW, 0 ≤ Q_i ≤ floor_i, and the result
    equals that lens run on a basin whose demands are the floors."""
    p = replace(lens_params("sufficientarian"), floorScaling=rule)
    for _ in range(100):
        s = random_schemes(RNG)
        floors = [p.floor * x.demandMm3 for x in s]
        AW = float(RNG.uniform(0, 1)) * sum(floors)
        Q = allocate("sufficientarian", s, AW, p, SCORING.survivalFloor).Q
        assert abs(sum(Q) - AW) <= 1e-5
        assert all(0 <= q <= f + 1e-6 for q, f in zip(Q, floors))
        on_floors = [replace(x, demandMm3=f) for x, f in zip(s, floors)]
        assert Q == allocate(FLOOR_RULES[rule], on_floors, AW, p, SCORING.survivalFloor).Q
