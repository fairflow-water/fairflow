# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Blueprint §2.4 — FAO-33 seasonal yield response (Doorenbos & Kassam 1979) with the survival branch."""

from __future__ import annotations

from .model import Scheme


def yield_of(s: Scheme, water_mm3: float, survival_floor: float) -> float:
    """Y = K(1 − K_y(1 − min(A, 1))) for A ≥ floor, else Y(floor)·A/floor, with A = W/D (§2.4)."""
    A = max(0.0, water_mm3) / s.demandMm3

    def fao33(a: float) -> float:
        return s.capacityT * (1 - s.ky * (1 - min(a, 1.0)))

    return fao33(A) if A >= survival_floor else fao33(survival_floor) * A / survival_floor


def value_of(s: Scheme, water_mm3: float, survival_floor: float) -> float:
    """p·Y (§2.3 utilitarian objective; §2.4 livelihood)."""
    return s.price * yield_of(s, water_mm3, survival_floor)
