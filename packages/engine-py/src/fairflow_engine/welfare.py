# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §2.7 — a posteriori welfare functions."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from .indicators import gini
from .model import Scheme


def pwf_ede(A: Sequence[float], gamma: float, supply_floor: float) -> float:
    """The equally-distributed equivalent of PWF_γ (Atkinson 1970) on s_i = min(A_i, 1) floored at `supply_floor`: the
    share of need which, given to every farm, is worth as much. γ = 0 is the mean (every share counts the same); γ = ∞
    is its limit, the smallest share (only the worst-off counts); γ = 1 is the geometric mean."""
    s = np.maximum(supply_floor, np.minimum(np.asarray(A, dtype=float), 1.0))
    if math.isinf(gamma):
        return float(s.min())
    if gamma == 1:
        return float(np.exp(np.log(s).mean()))
    return float(np.mean(s ** (1 - gamma)) ** (1 / (1 - gamma)))


def welfare(schemes: Sequence[Scheme], A: Sequence[float], gamma: float, m: float, supply_floor: float) -> dict[str, float]:
    """s_i = min(A_i, 1) floored at `supply_floor`; m_i = m.
    UWF = mean s; PWF_γ = Σ s^(1−γ)/(1−γ) (Atkinson 1970, increasing in supply) with its equally-distributed-equivalent
    PWFede; SWF = 0 if any s_i < m, else (1/2n)[Σ min(1, s/m) + Σ (s − m)/(1 − m)]; EWF = 1 − Gini(s), uncorrected,
    as the §3.1 fixtures use; CWF = Σ N_i s_i / Σ N_i."""
    s = np.maximum(supply_floor, np.minimum(np.asarray(A, dtype=float), 1.0))
    n = len(s)
    if gamma == 1:
        pwf = float(np.log(s).sum())
        ede = float(np.exp(pwf / n))
    else:
        pwf = float((s ** (1 - gamma) / (1 - gamma)).sum())
        ede = float(((1 - gamma) * pwf / n) ** (1 / (1 - gamma)))
    swf = 0.0 if (s < m).any() else float((np.minimum(1, s / m).sum() + ((s - m) / (1 - m)).sum()) / (2 * n))  # §2.7 SWF
    N = np.array([x.people for x in schemes], dtype=float)
    return {
        "UWF": float(s.mean()),
        "PWF": pwf,
        "PWFede": ede,
        "SWF": swf,
        "EWF": 1 - gini(s),
        "CWF": float((N * s).sum() / N.sum()),
    }
