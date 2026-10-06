# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §5.2 (S1) hard checks on a `scenario.json`: a basin that cannot be played is refused when it is built, never
mid-game. Values the scenario omits come from the sourced parameter registry. The worst-case coupling loss is computed
with the engine's own function, so the check cannot drift from the model."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .aquifer import inflow_loss_next
from .model import Basin


def basin_from_scenario(scenario: Mapping[str, Any], registry: Mapping[str, Any]) -> Basin:
    """The engine's Basin from a scenario's `basin` block, with registry defaults for anything the scenario omits."""
    b = scenario["basin"]
    a = b["aquifer"]
    pump = scenario.get("actions", {}).get("pump", {})
    return Basin.from_dict(
        {
            "reserve": b["reserve"]["value"],
            "aquifer": {
                "initial": a["initial"],
                "reserve": a["reserve"],
                "lowThreshold": a["lowThreshold"],
                "naturalRecharge": a["naturalRecharge"],
                "seatCostMultipliers": a.get("seatCostMultipliers", registry["basin.aquifer.seatCostMultipliers"]),
                "maxInflowLossMm3": a["gwSwCoupling"]["maxInflowLossMm3"] if a["gwSwCoupling"]["enabled"] else 0.0,
                "tankResolution": a.get("tankResolution", registry["basin.aquifer.tankResolution"]),
            },
            "pump": {
                "cap": pump.get("cap", registry["actions.pump.cap"]),
                "costBase": pump.get("costBase", registry["actions.pump.costBase"]),
                "costSlope": pump.get("costSlope", registry["actions.pump.costSlope"]),
            },
        }
    )


def worst_case_allocable(scenario: Mapping[str, Any], registry: Mapping[str, Any]) -> float:
    """Allocable water in the worst season the rules allow: the dry card, after the largest dry drift over the longest
    game, minus the largest GW–SW coupling loss (reached when the aquifer sits at its reserve floor), minus the reserve.

    `dryDrift` is read conservatively as a reduction of `gameLength.max` × drift; the blueprint (§2.2) says only that the
    dry inflow "falls by a fixed Mm³ per season"."""
    b = scenario["basin"]
    basin = basin_from_scenario(scenario, registry)
    drift = b["inflow"].get("dryDrift", 0.0) * b["gameLength"]["max"]
    largest_loss = inflow_loss_next(basin, basin.aquifer.reserve)
    return float(b["inflow"]["dry"] - drift - largest_loss - basin.reserve)


def hard_checks(scenario: Mapping[str, Any], registry: Mapping[str, Any]) -> list[str]:
    """Reasons to refuse the scenario (§5.2 S1); an empty list means it may be played."""
    b = scenario["basin"]
    problems: list[str] = []
    if b["reserve"].get("mode", "absolute") != "absolute":
        problems.append("reserve.mode 'fraction' is not supported yet; give the reserve in Mm³")
        return problems
    reserve, dry = b["reserve"]["value"], b["inflow"]["dry"]
    if reserve >= dry:
        problems.append(f"reserve ({reserve} Mm³) must be below the dry inflow ({dry} Mm³)")
    demand = sum(s["derived"]["demandMm3"] for s in scenario["schemes"])
    if dry - reserve >= demand:
        problems.append(
            f"no scarcity: the dry year leaves {dry - reserve} Mm³ for {demand} Mm³ of demand, so the lens never matters"
        )
    worst = worst_case_allocable(scenario, registry)
    if worst <= 0:
        problems.append(
            f"in the worst season the rules allow, no water is left to share ({worst:.3f} Mm³): dry inflow, minus the "
            "largest dry drift and coupling loss, must exceed the reserve"
        )
    return problems
