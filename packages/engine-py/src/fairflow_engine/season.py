# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint R9–R12 for one season without actions, modules or events; and the §2.7 verdict."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

from .allocate import allocate
from .aquifer import (
    aquifer_full,
    aquifer_spill,
    inflow_loss_next,
    next_stock,
    observed_stock,
    pump_cost_per_mm3,
    ration_pumps,
    return_flow,
)
from .indicators import efficiency, equity_pj, equity_se, gini, gini_corrected, sustainability, sustainability_band, triangle
from .model import Basin, LensId, LensParams, Scheme, Scoring, round6
from .production import yield_of
from .welfare import welfare


class ByEqualisandum(TypedDict):
    claimant: float
    hectare: float
    person: float


class ByBasis(TypedDict):
    consumed: float
    diverted: float


class Dials(TypedDict):
    ePJ: float
    eSE: ByEqualisandum
    F: ByBasis


class AllocationResult(TypedDict):
    lens: LensId
    Q: list[float]
    surplusToAquifer: float


class Triangle(TypedDict):
    r1: float
    r2: float
    r3: float
    area: float
    score: float


class WelfareScores(TypedDict):
    UWF: float
    PWF: float
    PWFede: float
    SWF: float
    EWF: float
    CWF: float


class SeasonResult(TypedDict):
    """Everything one season produces; record.py decides which fields are public during play (ADR 0004)."""

    observedStockNext: float
    aquiferFull: bool
    asAllocated: Dials
    sustainabilityBand: Literal["good", "warning", "unsustainable"]
    allocable: float
    allocation: AllocationResult
    pumpCost: list[float]
    P: list[float]
    W: list[float]
    A: list[float]
    Y: list[float]
    dL: list[float]
    pumpsTotal: float
    returnFlow: float
    stockNext: float
    spill: float
    inflowLossNext: float
    ePJ: float
    eSE: ByEqualisandum
    gini: float
    giniCorrected: float
    F: ByBasis
    S: float
    triangle: Triangle
    welfare: WelfareScores


class Verdict(TypedDict):
    voted: LensId
    satisfied: LensId
    distance: float
    pumpingGap: float


def _dials(schemes: Sequence[Scheme], W: Sequence[float], floor: float) -> Dials:
    r = round6
    return {
        "ePJ": r(equity_pj(schemes, W)),
        "eSE": {
            "claimant": r(equity_se(schemes, W, "claimant")),
            "hectare": r(equity_se(schemes, W, "hectare")),
            "person": r(equity_se(schemes, W, "person")),
        },
        "F": {
            "consumed": r(efficiency(schemes, W, "consumed", floor)),
            "diverted": r(efficiency(schemes, W, "diverted", floor)),
        },
    }


def resolve_season(
    schemes: Sequence[Scheme],
    basin: Basin,
    inflow: float,
    stock: float,
    lens: LensId,
    lens_params: LensParams,
    pumps: Sequence[float],
    scoring: Scoring,
) -> SeasonResult:
    """Allocate, ration pumps, deliver, produce, score and step the aquifer. Every output rounded to 1e-6 (§7.2)."""
    if len(pumps) != len(schemes):
        raise ValueError("pumps: one value per scheme")
    floor = scoring.survivalFloor
    allocable = max(0.0, inflow - basin.reserve)
    alloc = allocate(lens, schemes, allocable, lens_params, floor)
    cost = [pump_cost_per_mm3(basin, stock, s.seat) for s in schemes]
    P = ration_pumps(basin, stock, pumps)
    W = [q + p for q, p in zip(alloc.Q, P, strict=True)]
    A = [w / s.demandMm3 for s, w in zip(schemes, W, strict=True)]
    Y = [yield_of(s, w, floor) for s, w in zip(schemes, W, strict=True)]
    dL = [s.price * y / 100 - c * p for s, y, c, p in zip(schemes, Y, cost, P, strict=True)]  # §2.4 ΔL = pY/100 − c_p P
    pumped = sum(P)
    returns = return_flow(schemes, W)
    stock_next = next_stock(basin, stock, alloc.surplusToAquifer, returns, pumped)
    spill = aquifer_spill(basin, stock, alloc.surplusToAquifer, returns, pumped)
    e_pj = equity_pj(schemes, W)
    S = sustainability(schemes, W, allocable, basin.aquifer.naturalRecharge)
    s_capped = [max(scoring.welfareSupplyFloor, min(a, 1.0)) for a in A]
    tri = triangle(e_pj, efficiency(schemes, W, "consumed", floor), S, scoring.r3Ramp)
    wf = welfare(schemes, A, scoring.welfareGamma, floor, scoring.welfareSupplyFloor)
    actual = _dials(schemes, W, floor)
    r = round6
    return {
        "observedStockNext": r(observed_stock(basin, stock_next)),
        "aquiferFull": aquifer_full(basin, stock_next),
        "asAllocated": _dials(schemes, list(alloc.Q), floor),  # ADR 0004: the in-play dials, on the public allocation
        "sustainabilityBand": sustainability_band(S, scoring.sustainabilityBands),
        "allocable": r(allocable),
        "allocation": {"lens": lens, "Q": list(alloc.Q), "surplusToAquifer": alloc.surplusToAquifer},
        "pumpCost": [r(x) for x in cost],
        "P": [r(x) for x in P],
        "W": [r(x) for x in W],
        "A": [r(x) for x in A],
        "Y": [r(x) for x in Y],
        "dL": [r(x) for x in dL],
        "pumpsTotal": r(pumped),
        "returnFlow": r(returns),
        "stockNext": r(stock_next),
        "spill": r(spill),
        "inflowLossNext": r(inflow_loss_next(basin, stock_next)),
        "ePJ": actual["ePJ"],
        "eSE": actual["eSE"],
        "gini": r(gini(s_capped)),
        "giniCorrected": r(gini_corrected(s_capped)),
        "F": actual["F"],
        "S": r(S),
        "triangle": {
            "r1": r(tri["r1"]),
            "r2": r(tri["r2"]),
            "r3": r(tri["r3"]),
            "area": r(tri["area"]),
            "score": r(tri["score"]),
        },
        "welfare": {
            "UWF": r(wf["UWF"]),
            "PWF": r(wf["PWF"]),
            "PWFede": r(wf["PWFede"]),
            "SWF": r(wf["SWF"]),
            "EWF": r(wf["EWF"]),
            "CWF": r(wf["CWF"]),
        },
    }


def verdict(
    schemes: Sequence[Scheme],
    allocable: float,
    W: Sequence[float],
    voted: LensId,
    pumping_gap: float,
    lenses: Sequence[tuple[LensId, LensParams]],
    survival_floor: float,
) -> Verdict:
    """§2.7: the lens whose ideal allocation is nearest the realised one by Σ|A_i − A_i*|. Ties go to the voted lens,
    then to the earlier card: two lenses can prescribe the same allocation (a proportional cut of the sufficientarian
    floors is the proportional lens), and the table's own rule must then be named (review 2026-10-08, E1).
    `lenses` must carry the parameters actually applied, including the floor rule the table voted."""
    A = [w / s.demandMm3 for s, w in zip(schemes, W, strict=True)]
    distances: list[tuple[LensId, float]] = []
    for lens, params in lenses:
        ideal = allocate(lens, schemes, allocable, params, survival_floor).Q
        distances.append((lens, sum(abs(a - q / s.demandMm3) for a, q, s in zip(A, ideal, schemes, strict=True))))
    if not distances:
        raise ValueError("verdict: no lenses to compare")
    nearest = min(d for _, d in distances)
    tied = [lens for lens, d in distances if d <= nearest + 1e-9]  # tolerance: 1e-9 on a sum of rounded shares (§7.2)
    satisfied = voted if voted in tied else tied[0]
    return {"voted": voted, "satisfied": satisfied, "distance": dict(distances)[satisfied], "pumpingGap": pumping_gap}
