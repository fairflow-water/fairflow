# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §2.3 — the allocation lenses as a generic claims-problem solver (claims D_i, estate AW)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, brentq, milp

from .model import LensId, LensParams, MissingParameter, Scheme, round6
from .production import value_of

ROOT_XTOL = 1e-12  # tolerance of the root finder for λ (far below the 1e-6 rounding)
LEXIMIN_TOL = 1e-7  # tolerance: adequacy levels equal to within the solver's feasibility tolerance (HiGHS 1e-7)
MILP_GAP = 1e-9  # tolerance: HiGHS stops at a 1e-4 relative gap by default; require the optimum


@dataclass(frozen=True)
class Allocation:
    lens: LensId
    Q: tuple[float, ...]
    surplusToAquifer: float


def weighted_cea(claims: Sequence[float], weights: Sequence[float], estate: float) -> list[float]:
    """§2.3: Q_i = min(D_i, C_i/Σ_{j∈U} C_j · AW^(k)), iterated over the uncapped set U until no cap binds."""
    D = np.asarray(claims, dtype=float)
    C = np.asarray(weights, dtype=float)
    if np.any((D > 0) & (C <= 0)):  # review E4: a zero weight leaves Σ C_j = 0 once the others are capped
        raise ValueError("weighted_cea: every positive claim needs a positive weight")
    Q = np.zeros_like(D)
    target = min(estate, D.sum())
    uncapped = np.ones(len(D), dtype=bool)
    while uncapped.any():
        remaining = target - Q.sum()
        share = np.where(uncapped, C / C[uncapped].sum() * remaining, 0.0)
        binds = uncapped & (share >= D - Q)
        if not binds.any():
            Q = Q + share
            break
        Q[binds] = D[binds]
        uncapped &= ~binds
    return [round6(q) for q in Q]


def cel(claims: Sequence[float], estate: float) -> list[float]:
    """§2.3 equal sacrifice, constrained equal losses: Σ max(0, D_i − λ) = AW (Thomson 2003). λ by Brent's method."""
    D = np.asarray(claims, dtype=float)
    if estate >= D.sum():
        return [round6(d) for d in D]
    lam = brentq(lambda x: np.maximum(0.0, D - x).sum() - estate, 0.0, float(D.max()), xtol=ROOT_XTOL)
    return [round6(x) for x in np.maximum(0.0, D - lam)]


def talmud(claims: Sequence[float], estate: float) -> list[float]:
    """§2.3 Talmud (Aumann & Maschler 1985): AW ≤ ½ΣD: CEA on half-claims; else D_i/2 + CEL on half-claims."""
    half = [d / 2 for d in claims]  # §2.3 Talmud half-claims
    if estate <= sum(claims) / 2:  # §2.3 'AW ≤ ½ΣD'
        return weighted_cea(half, [1.0] * len(half), estate)
    rest = cel(half, estate - sum(claims) / 2)  # §2.3 Talmud: D_i/2 + CEL on half-claims
    return [round6(h + r) for h, r in zip(half, rest, strict=True)]


def weights_for(lens: LensId, schemes: Sequence[Scheme], params: LensParams) -> list[float]:
    """§2.3 weights C_i of the weighted-CEA lenses."""
    if lens == "egalitarian":
        return [1.0 for _ in schemes]
    if lens == "proportional":
        return [s.demandMm3 for s in schemes]
    if lens == "weighted_utilitarian":
        return [s.capacityT / s.demandMm3 for s in schemes]
    if lens == "capability":
        return [s.people * s.kappa for s in schemes]
    if lens == "prioritarian":
        # Q_i ∝ w_i^(1/γ) D_i^(1−1/γ)
        gamma = params.need("gamma", lens)
        weight = params.need("weight", lens)
        if not gamma >= 1:
            raise ValueError(f"prioritarian: gamma must be ≥ 1, got {gamma}")
        w = [1.0 if weight == "1" else s.people for s in schemes]
        return [wi ** (1 / gamma) * s.demandMm3 ** (1 - 1 / gamma) for wi, s in zip(w, schemes, strict=True)]
    raise ValueError(f"{lens} is not a weight rule")


def max_value(
    schemes: Sequence[Scheme], estate: float, survival_floor: float, lower: Sequence[float] | None = None
) -> list[float]:
    """§2.3 utilitarian: maximise Σ p_i Y_i subject to lower_i ≤ Q_i ≤ D_i and Σ Q_i = min(AW, ΣD).

    Y_i is piecewise linear in Q_i with a kink at survival_floor·D_i and is not concave there, so this is a
    mixed-integer LP (standard piecewise-linear formulation with one binary per scheme), solved by HiGHS through
    scipy.optimize.milp. Segment slopes are read off the production function itself, not written out by hand.
    """
    n = len(schemes)
    lo = list(lower) if lower is not None else [0.0] * n
    D = np.array([s.demandMm3 for s in schemes])
    L = survival_floor * D  # end of the survival segment
    H = D - L  # length of the FAO-33 segment
    a = np.array([value_of(s, seg, survival_floor) / seg if seg > 0 else 0.0 for s, seg in zip(schemes, L, strict=True)])
    b = np.array(
        [
            (value_of(s, d, survival_floor) - value_of(s, seg, survival_floor)) / h if h > 0 else 0.0
            for s, d, seg, h in zip(schemes, D, L, H, strict=True)
        ]
    )
    budget = min(estate, float(D.sum()))
    # variables: x1 (n), x2 (n), z (n)
    c = np.concatenate([-a, -b, np.zeros(n)])
    eye, Z = np.eye(n), np.zeros((n, n))
    A = np.vstack(
        [
            np.hstack([Z, eye, -np.diag(H)]),  # x2 − H z ≤ 0
            np.hstack([eye, Z, -np.diag(L)]),  # x1 − L z ≥ 0
            np.hstack([np.ones((1, n)), np.ones((1, n)), np.zeros((1, n))]),  # Σ Q = budget
            np.hstack([eye, eye, Z]),  # Q_i ≥ lower_i
        ]
    )
    lb = np.concatenate([np.full(n, -np.inf), np.zeros(n), [budget], lo])
    ub = np.concatenate([np.zeros(n), np.full(n, np.inf), [budget], np.full(n, np.inf)])
    res = milp(
        c,
        constraints=LinearConstraint(A, lb, ub),
        integrality=np.concatenate([np.zeros(2 * n), np.ones(n)]),  # layout: x1, x2 continuous; z binary
        bounds=Bounds(np.zeros(3 * n), np.concatenate([L, H, np.ones(n)])),  # layout: 3 blocks of n
        options={"mip_rel_gap": MILP_GAP},
    )
    if not res.success:
        raise ValueError(f"max_value: no feasible allocation ({res.message})")
    x = res.x
    per_scheme = [{round(float(a[i]), 9), round(float(b[i]), 9)} for i in range(n)]  # rounding: 1e-9 t per Mm³
    if sum(len(x) for x in per_scheme) == len(set().union(*per_scheme)):  # no slope shared by two schemes: unique
        return [round6(x[i] + x[n + i]) for i in range(n)]
    # Review E5 (maintainer decision 2026-10-08): equal marginal values make the optimum non-unique; among the optimal
    # allocations take the leximin one in adequacy (equal adequacy among the tied farms), so the result is canonical.
    best = float(-res.fun)
    tol = MILP_GAP * max(1.0, abs(best))
    fixed: dict[int, float] = {}
    while len(fixed) < n:
        free = [i for i in range(n) if i not in fixed]
        stage = (c, A, lb, ub, L, H, D, best - tol, fixed)
        level = _adequacy_stage(*stage, objective=None, level=0.0)
        pinned = [i for i in free if _adequacy_stage(*stage, objective=i, level=level) <= level + LEXIMIN_TOL]
        for i in pinned or free:
            fixed[i] = level
    Q = np.array([fixed[i] for i in range(n)]) * D
    Q = np.minimum(D, Q * budget / Q.sum()) if Q.sum() > 0 else Q  # close Σ Q = budget after the solver tolerances
    return [round6(q) for q in Q]


def _adequacy_stage(
    c: np.ndarray,
    A: np.ndarray,
    lb: np.ndarray,
    ub: np.ndarray,
    L: np.ndarray,
    H: np.ndarray,
    D: np.ndarray,
    least_value: float,
    fixed: dict[int, float],
    objective: int | None,
    level: float,
) -> float:
    """One leximin stage over the optimal set {Σ value ≥ least_value}: maximise the common floor t of the free schemes'
    adequacy (objective None), or one free scheme's adequacy with the other free schemes held at `level` (objective i)."""
    n = len(D)
    k = 3 * n + 1  # layout: x1, x2, z, t
    value = np.concatenate([-c[: 2 * n], np.zeros(n + 1)])  # layout: x1, x2 values; z, t carry none
    rows = [np.hstack([A, np.zeros((A.shape[0], 1))]), value[None, :]]
    lows: list[np.ndarray] = [lb, np.array([least_value])]
    highs: list[np.ndarray] = [ub, np.array([np.inf])]
    for i in range(n):
        row = np.zeros(k)
        row[i] = row[n + i] = 1.0 / D[i]  # A_i = (x1_i + x2_i) / D_i
        if i in fixed:
            lows.append(np.array([fixed[i] - LEXIMIN_TOL]))
            highs.append(np.array([fixed[i] + LEXIMIN_TOL]))
        elif objective is None or i != objective:
            row[-1] = -1.0 if objective is None else 0.0
            lows.append(np.array([0.0 if objective is None else level - LEXIMIN_TOL]))
            highs.append(np.array([np.inf]))
        else:
            continue
        rows.append(row[None, :])
    goal = np.zeros(k)
    if objective is None:
        goal[-1] = -1.0
    else:
        goal[objective] = goal[n + objective] = -1.0 / D[objective]
    res = milp(
        goal,
        constraints=LinearConstraint(np.vstack(rows), np.concatenate(lows), np.concatenate(highs)),
        integrality=np.concatenate([np.zeros(2 * n), np.ones(n), [0]]),  # layout: x1, x2 continuous; z binary; t
        bounds=Bounds(np.zeros(k), np.concatenate([L, H, np.ones(n), [np.inf]])),  # layout: 3 blocks of n, then t
        options={"mip_rel_gap": MILP_GAP},
    )
    if not res.success:
        raise ValueError(f"max_value: leximin stage failed ({res.message})")
    return float(-res.fun)


# ADR 0003 floor-shortfall options → the §2.3 lens that cuts the floors.
FLOOR_RULES: dict[str, LensId] = {
    "proportional": "proportional",
    "cea": "egalitarian",
    "cel": "equal_sacrifice",
    "talmud": "talmud",
    "capability": "capability",
}


def sufficientarian(schemes: Sequence[Scheme], estate: float, params: LensParams, survival_floor: float) -> list[float]:
    """§2.3: floor·D_i for all (proportional scaling or CEA on floors if short), remainder by a secondary rule."""
    lens = "sufficientarian"
    D = [s.demandMm3 for s in schemes]
    floors = [params.need("floor", lens) * d for d in D]
    if sum(floors) >= estate:
        # ADR 0003: the table chooses how the floors are cut, among the §2.3 claims rules applied to the floors as claims.
        rule = params.need("floorScaling", lens)
        if rule not in FLOOR_RULES:
            raise ValueError(f"sufficientarian: floorScaling must be one of {sorted(FLOOR_RULES)}, got {rule!r}")
        on_floors = [replace(s, demandMm3=f) for s, f in zip(schemes, floors, strict=True)]
        return list(allocate(FLOOR_RULES[rule], on_floors, estate, params, survival_floor).Q)
    secondary = params.need("secondary", lens)
    if secondary == "max_value":
        return max_value(schemes, estate, survival_floor, lower=floors)
    residual = [d - f for d, f in zip(D, floors, strict=True)]
    weights = weights_for("prioritarian", schemes, params) if secondary == "prioritarian" else residual
    extra = weighted_cea(residual, weights, estate - sum(floors))
    return [round6(f + e) for f, e in zip(floors, extra, strict=True)]


def allocate(
    lens: LensId, schemes: Sequence[Scheme], allocable: float, params: LensParams, survival_floor: float
) -> Allocation:
    """Every lens of §2.3 except user-defined criteria (the §6.1 grammar). Surplus = max(0, AW − ΣD) (§2.6)."""
    D = [s.demandMm3 for s in schemes]
    if lens == "equal_sacrifice":
        Q = cel(D, allocable)
    elif lens == "talmud":
        Q = talmud(D, allocable)
    elif lens == "utilitarian":
        Q = max_value(schemes, allocable, survival_floor)
    elif lens == "sufficientarian":
        Q = sufficientarian(schemes, allocable, params, survival_floor)
    else:
        Q = weighted_cea(D, weights_for(lens, schemes, params), allocable)
    return Allocation(lens, tuple(Q), round6(max(0.0, allocable - sum(D))))


__all__ = [
    "FLOOR_RULES",
    "Allocation",
    "MissingParameter",
    "allocate",
    "cel",
    "max_value",
    "sufficientarian",
    "talmud",
    "weighted_cea",
    "weights_for",
]
