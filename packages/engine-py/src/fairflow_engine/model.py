# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Inputs of the model (blueprint §2.1–2.2, §6.1). No field has a default: every value comes from a scenario
or the parameter registry, each with a source. Missing values are errors, never silently filled."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

LensId = Literal[
    "utilitarian",
    "weighted_utilitarian",
    "egalitarian",
    "proportional",
    "capability",
    "sufficientarian",
    "prioritarian",
    "equal_sacrifice",
    "talmud",
]


HA_MM_TO_MM3 = 1e-5  # §2.2 "Area × gross seasonal depth": 1 ha × 1 mm = 10 m³ = 1e-5 Mm³ (unit conversion)


class MissingParameter(ValueError):
    """A parameter the computation needs was not supplied by the scenario or the registry."""


@dataclass(frozen=True)
class Scheme:
    id: str
    name: str
    seat: int
    demandMm3: float  # D_i
    capacityT: float  # K_i
    ky: float  # FAO-33 K_y
    beta: float  # consumptive fraction
    people: float
    kappa: float
    price: float
    areaHa: float
    # ADR 0008: pumping energy per m³ relative to the most efficient pump set (η_ref / η_i), applied always
    pumpCostFactor: float = 1.0
    # ADR 0008: the scheme's wells stop delivering when the observed stock is at or below this level (suction limit of
    # shallow wells); None = wells deep enough for the whole game
    wellsFailAtOrBelow: float | None = None

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> Scheme:
        optional = {"pumpCostFactor", "wellsFailAtOrBelow"}
        fields = Scheme.__dataclass_fields__
        return Scheme(**{k: d[k] for k in fields if k not in optional}, **{k: d[k] for k in optional if k in d})


@dataclass(frozen=True)
class Aquifer:
    initial: float
    reserve: float
    lowThreshold: float
    naturalRecharge: float
    seatCostMultipliers: tuple[float, ...]
    maxInflowLossMm3: float
    tankResolution: float  # ADR 0004: resolution of the observed level (prices pumping, drives coupling)
    capacity: float | None = None  # ADR 0006: B_max, recharge beyond it is rejected; None = unbounded (§2.6 as written)
    returnRecharge: float = (
        1.0  # share of non-consumed water that recharges the shared aquifer; the rest leaves the basin (ADR 0007)
    )
    # ADR 0008: baseflow lost per Mm³ of storage below B₀ (capture of streamflow, Konikow & Leake 2014); None = the
    # §2.2 rule, maxInflowLossMm3 scaled over the storage below B_low
    baseflowLossPerMm3: float | None = None


@dataclass(frozen=True)
class Pump:
    cap: float
    costBase: float
    costSlope: float
    capShare: float | None = None  # ADR 0008: well capacity as a share of the scheme's demand; None = the flat cap


@dataclass(frozen=True)
class Basin:
    reserve: float
    aquifer: Aquifer
    pump: Pump

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> Basin:
        a = d["aquifer"]
        return Basin(
            reserve=d["reserve"],
            aquifer=Aquifer(
                a["initial"],
                a["reserve"],
                a["lowThreshold"],
                a["naturalRecharge"],
                tuple(a["seatCostMultipliers"]),
                a["maxInflowLossMm3"],
                a["tankResolution"],
                a.get("capacity"),
                a.get("returnRecharge", 1.0),
                a.get("baseflowLossPerMm3"),
            ),
            pump=Pump(d["pump"]["cap"], d["pump"]["costBase"], d["pump"]["costSlope"], d["pump"].get("capShare")),
        )


@dataclass(frozen=True)
class Scoring:
    r3Ramp: float  # §2.5
    welfareGamma: float  # §2.7 PWF_γ
    survivalFloor: float  # §2.4 survival threshold; §2.7 m_i
    welfareSupplyFloor: float  # §2.7 "s_i = min(A_i, 1) floored at …"
    sustainabilityBands: tuple[float, float]  # §2.2 band edges; ADR 0004 shows S during play as its band word only

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> Scoring:
        missing = [k for k in Scoring.__dataclass_fields__ if k not in d]
        if missing:
            raise MissingParameter(f"scoring needs {missing}")
        low, high = d["sustainabilityBands"]
        return Scoring(
            r3Ramp=d["r3Ramp"],
            welfareGamma=d["welfareGamma"],
            survivalFloor=d["survivalFloor"],
            welfareSupplyFloor=d["welfareSupplyFloor"],
            sustainabilityBands=(low, high),
        )


@dataclass(frozen=True)
class LensParams:
    """Per-lens parameters (§6.1 `lenses[]`). Required only by the lens that uses them; None means not supplied."""

    gamma: float | None = None
    weight: Literal["1", "people"] | None = None
    floor: float | None = None
    floorScaling: Literal["proportional", "cea", "cel", "talmud", "capability"] | None = None  # ADR 0003
    secondary: Literal["max_value", "prioritarian", "proportional"] | None = None

    @staticmethod
    def from_dict(d: Mapping[str, Any] | None) -> LensParams:
        return LensParams(**(d or {}))

    def need(self, name: str, lens: str) -> Any:
        value = getattr(self, name)
        if value is None:
            raise MissingParameter(f"lens {lens} needs parameter {name!r}")
        return value


def round6(x: float) -> float:
    """§7.2 — every stored number rounded to 1e-6 at the event boundary, half up (as the TypeScript mirror does)."""
    return math.floor(x * 1e6 + 0.5) / 1e6  # §7.2 rounding to 1e-6, half up
