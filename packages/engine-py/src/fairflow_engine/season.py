# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Blueprint R9–R12 for one season without actions, modules or events; and the §2.7 verdict."""

from __future__ import annotations

from typing import Sequence

from .allocate import allocate
from .aquifer import inflow_loss_next, next_stock, pump_cost_per_mm3, ration_pumps, return_flow
from .indicators import efficiency, equity_pj, equity_se, gini, gini_corrected, sustainability, triangle
from .model import Basin, LensId, LensParams, Scheme, Scoring, round6
from .production import yield_of
from .welfare import welfare


def resolve_season(schemes: Sequence[Scheme], basin: Basin, inflow: float, stock: float, lens: LensId,
                   lens_params: LensParams, pumps: Sequence[float], scoring: Scoring) -> dict:
    """Allocate, ration pumps, deliver, produce, score and step the aquifer. Every output rounded to 1e-6 (§7.2)."""
    if len(pumps) != len(schemes):
        raise ValueError("pumps: one value per scheme")
    floor = scoring.survivalFloor
    allocable = max(0.0, inflow - basin.reserve)
    alloc = allocate(lens, schemes, allocable, lens_params, floor)
    cost = [pump_cost_per_mm3(basin, stock, s.seat) for s in schemes]
    P = ration_pumps(basin, stock, pumps)
    W = [q + p for q, p in zip(alloc.Q, P)]
    A = [w / s.demandMm3 for s, w in zip(schemes, W)]
    Y = [yield_of(s, w, floor) for s, w in zip(schemes, W)]
    dL = [s.price * y / 100 - c * p for s, y, c, p in zip(schemes, Y, cost, P)]
    pumped = sum(P)
    returns = return_flow(schemes, W)
    stock_next = next_stock(basin, stock, alloc.surplusToAquifer, returns, pumped)
    e_pj = equity_pj(schemes, W)
    F = {"consumed": efficiency(schemes, W, "consumed", floor), "diverted": efficiency(schemes, W, "diverted", floor)}
    S = sustainability(schemes, W, allocable, basin.aquifer.naturalRecharge)
    s_capped = [max(scoring.welfareSupplyFloor, min(a, 1.0)) for a in A]
    tri = triangle(e_pj, F["consumed"], S, scoring.r3Ramp)
    wf = welfare(schemes, A, scoring.welfareGamma, floor, scoring.welfareSupplyFloor)
    r = round6
    return {
        "allocable": r(allocable),
        "allocation": {"lens": lens, "Q": list(alloc.Q), "surplusToAquifer": alloc.surplusToAquifer},
        "pumpCost": [r(x) for x in cost], "P": [r(x) for x in P], "W": [r(x) for x in W], "A": [r(x) for x in A],
        "Y": [r(x) for x in Y], "dL": [r(x) for x in dL],
        "pumpsTotal": r(pumped), "returnFlow": r(returns), "stockNext": r(stock_next),
        "inflowLossNext": r(inflow_loss_next(basin, stock_next)),
        "ePJ": r(e_pj), "eSE": {u: r(equity_se(schemes, W, u)) for u in ("claimant", "hectare", "person")},
        "gini": r(gini(s_capped)), "giniCorrected": r(gini_corrected(s_capped)),
        "F": {k: r(v) for k, v in F.items()}, "S": r(S),
        "triangle": {k: r(v) for k, v in tri.items()},
        "welfare": {k: r(v) for k, v in wf.items()},
    }


def verdict(schemes: Sequence[Scheme], allocable: float, W: Sequence[float], voted: LensId, pumping_gap: float,
            lenses: Sequence[tuple[LensId, LensParams]], survival_floor: float) -> dict:
    """§2.7: the lens whose ideal allocation is nearest the realised one by Σ|A_i − A_i*|; ties to the earlier card."""
    A = [w / s.demandMm3 for s, w in zip(schemes, W)]
    best = None
    for lens, params in lenses:
        ideal = allocate(lens, schemes, allocable, params, survival_floor).Q
        d = sum(abs(a - q / s.demandMm3) for a, q, s in zip(A, ideal, schemes))
        if best is None or d < best["distance"] - 1e-9:
            best = {"voted": voted, "satisfied": lens, "distance": d, "pumpingGap": pumping_gap}
    if best is None:
        raise ValueError("verdict: no lenses to compare")
    return best
