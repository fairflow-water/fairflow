# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Inputs of the model (blueprint §2.1–2.2, §6.1). No field has a default: every value comes from a scenario
or the parameter registry, each with a source. Missing values are errors, never silently filled."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

LensId = Literal[
    "utilitarian", "weighted_utilitarian", "egalitarian", "proportional", "capability",
    "sufficientarian", "prioritarian", "equal_sacrifice", "talmud",
]


class MissingParameter(ValueError):
    """A parameter the computation needs was not supplied by the scenario or the registry."""


@dataclass(frozen=True)
class Scheme:
    id: str
    name: str
    seat: int
    demandMm3: float   # D_i
    capacityT: float   # K_i
    ky: float          # FAO-33 K_y
    beta: float        # consumptive fraction
    people: float
    kappa: float
    price: float
    areaHa: float

    @staticmethod
    def from_dict(d: dict) -> "Scheme":
        return Scheme(**{k: d[k] for k in Scheme.__dataclass_fields__})


@dataclass(frozen=True)
class Aquifer:
    initial: float
    reserve: float
    lowThreshold: float
    naturalRecharge: float
    seatCostMultipliers: tuple[float, ...]
    maxInflowLossMm3: float


@dataclass(frozen=True)
class Pump:
    cap: float
    costBase: float
    costSlope: float


@dataclass(frozen=True)
class Basin:
    reserve: float
    aquifer: Aquifer
    pump: Pump

    @staticmethod
    def from_dict(d: dict) -> "Basin":
        a = d["aquifer"]
        return Basin(
            reserve=d["reserve"],
            aquifer=Aquifer(a["initial"], a["reserve"], a["lowThreshold"], a["naturalRecharge"],
                            tuple(a["seatCostMultipliers"]), a["maxInflowLossMm3"]),
            pump=Pump(d["pump"]["cap"], d["pump"]["costBase"], d["pump"]["costSlope"]),
        )


@dataclass(frozen=True)
class Scoring:
    r3Ramp: float              # §2.5
    welfareGamma: float        # §2.7 PWF_γ
    survivalFloor: float       # §2.4 survival threshold; §2.7 m_i
    welfareSupplyFloor: float  # §2.7 "s_i = min(A_i, 1) floored at …"

    @staticmethod
    def from_dict(d: dict) -> "Scoring":
        missing = [k for k in Scoring.__dataclass_fields__ if k not in d]
        if missing:
            raise MissingParameter(f"scoring needs {missing}")
        return Scoring(**{k: d[k] for k in Scoring.__dataclass_fields__})


@dataclass(frozen=True)
class LensParams:
    """Per-lens parameters (§6.1 `lenses[]`). Required only by the lens that uses them; None means not supplied."""
    gamma: Optional[float] = None
    weight: Optional[Literal["1", "people"]] = None
    floor: Optional[float] = None
    floorScaling: Optional[Literal["proportional", "cea", "cel", "talmud", "capability"]] = None  # ADR 0003
    secondary: Optional[Literal["max_value", "prioritarian", "proportional"]] = None

    @staticmethod
    def from_dict(d: Optional[dict]) -> "LensParams":
        return LensParams(**(d or {}))

    def need(self, name: str, lens: str):
        value = getattr(self, name)
        if value is None:
            raise MissingParameter(f"lens {lens} needs parameter {name!r}")
        return value


def round6(x: float) -> float:
    """§7.2 — every stored number rounded to 1e-6 at the event boundary, half up (as the TypeScript mirror does)."""
    return math.floor(x * 1e6 + 0.5) / 1e6  # §7.2 rounding to 1e-6, half up
