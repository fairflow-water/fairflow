# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Blueprint §2.5 — equity, efficiency and sustainability indicators and the triangle score."""

from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

from .model import Scheme
from .production import value_of

Equalisandum = Literal["claimant", "hectare", "person"]


def one_minus_cv(values: Sequence[float]) -> float:
    """1 − σ/μ with the population SD (§2.5). Unbounded below. All-zero values count as perfectly equal."""
    v = np.asarray(values, dtype=float)
    m = v.mean()
    return 1.0 if m == 0 else float(1 - v.std(ddof=0) / m)


def gini(values: Sequence[float]) -> float:
    """Gini coefficient Σ_i Σ_j |x_i − x_j| / (2 n² μ), no small-sample correction."""
    v = np.asarray(values, dtype=float)
    m = v.mean()
    return 0.0 if m == 0 else float(np.abs(v[:, None] - v[None, :]).sum() / (2 * len(v) ** 2 * m))  # §2.5 Gini definition


def gini_corrected(values: Sequence[float]) -> float:
    """Gini with the n/(n − 1) correction reported beside the needles (§2.5)."""
    return gini(values) * len(values) / (len(values) - 1)


def equity_pj(schemes: Sequence[Scheme], W: Sequence[float]) -> float:
    """E_PJ = 1 − σ(A)/Ā on adequacy A = W/D (Cherry 2025 Eq. 3-13)."""
    return one_minus_cv([w / s.demandMm3 for s, w in zip(schemes, W)])


def equity_se(schemes: Sequence[Scheme], W: Sequence[float], u: Equalisandum) -> float:
    """E_SE(u) = 1 − σ(W/u)/mean(W/u), u ∈ {1, ha_i, N_i}."""
    unit = {"claimant": lambda s: 1.0, "hectare": lambda s: s.areaHa, "person": lambda s: s.people}[u]
    return one_minus_cv([w / unit(s) for s, w in zip(schemes, W)])


def efficiency(schemes: Sequence[Scheme], W: Sequence[float], basis: Literal["consumed", "diverted"], survival_floor: float) -> float:
    """F = (Σ p_iY_i / Σ β_iW_i) / (Σ p_iK_i / Σ β_iD_i); `diverted` drops β (§2.5)."""
    beta = np.array([s.beta if basis == "consumed" else 1.0 for s in schemes])
    Wv = np.asarray(W, dtype=float)
    used = float((beta * Wv).sum())
    if used == 0:
        return 0.0
    realised = sum(value_of(s, w, survival_floor) for s, w in zip(schemes, W)) / used
    design = sum(s.price * s.capacityT for s in schemes) / float((beta * [s.demandMm3 for s in schemes]).sum())
    return realised / design


def sustainability(schemes: Sequence[Scheme], W: Sequence[float], allocable: float, natural_recharge: float) -> float:
    """S = Σ β_iW_i / (β* AW_t + r₀), β* the demand-weighted mean consumptive fraction (§2.5)."""
    beta = np.array([s.beta for s in schemes])
    D = np.array([s.demandMm3 for s in schemes])
    beta_star = float((beta * D).sum() / D.sum())
    return float((beta * np.asarray(W, dtype=float)).sum()) / (beta_star * allocable + natural_recharge)


def triangle(e_pj: float, F: float, S: float, r3_ramp: float) -> dict[str, float]:
    """§2.5: r₁ = max(E_PJ, 0) (clipped to [0, 1] before any composite), r₂ = min(F, 1), r₃ = 1 − clip((S − 1)/ramp, 0, 1);
    area (√3/4)(r₁r₂ + r₂r₃ + r₃r₁); score = geometric mean (r₁r₂r₃)^(1/3)."""
    r1, r2 = float(np.clip(e_pj, 0, 1)), float(np.clip(F, 0, 1))
    r3 = 1 - float(np.clip((S - 1) / r3_ramp, 0, 1))
    return {"r1": r1, "r2": r2, "r3": r3, "area": float(np.sqrt(3) / 4 * (r1 * r2 + r2 * r3 + r3 * r1)),  # §2.5 triangle area
            "score": float(np.cbrt(r1 * r2 * r3))}


def sustainability_band(S: float, edges: Sequence[float]) -> str:
    """§2.2 'sustainability good ≤ 1.00 / warning 1.00–1.15 / unsustainable > 1.15', with the edges from the registry."""
    return "good" if S <= edges[0] else "warning" if S <= edges[1] else "unsustainable"


def collective_score(season_scores: Sequence[float]) -> float:
    """R14: mean over seasons of the per-season geometric mean."""
    return float(np.mean(season_scores)) if len(season_scores) else 0.0
