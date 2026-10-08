# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §5.2 (S1) hard checks on a `scenario.json`: a basin that cannot be played is refused when it is built, never
mid-game. Values the scenario omits come from the sourced parameter registry. The worst-case coupling loss is computed
with the engine's own function, so the check cannot drift from the model."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any, cast

from jsonschema import Draft202012Validator

from .allocate import FLOOR_RULES
from .aquifer import inflow_loss_next
from .model import Basin, LensId, LensParams, Scheme, Scoring
from .record import GameSetup


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
                "capacity": a.get("capacity", a["initial"]),  # ADR 0006: omitted means full at the start
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
    # review E3: these options are in the schema but not in the engine yet; refuse rather than play them as stationary
    if b["inflow"].get("dryDrift", 0.0) != 0:
        problems.append("inflow.dryDrift is not implemented yet: the dry inflow would not fall; set it to 0")
    for flag in ("surplusRecharge", "returnFlows"):
        if b["aquifer"].get(flag, True) is not True:
            problems.append(f"aquifer.{flag} = false is not implemented yet: the engine always applies it")
    a = b["aquifer"]
    capacity = a.get("capacity", a["initial"])
    if a["initial"] < a["reserve"]:  # review E2: below B_res the §2.6 floor max(B_res, ·) would create water
        problems.append(f"aquifer initial stock ({a['initial']} Mm³) is below its reserve ({a['reserve']} Mm³)")
    if capacity < a["initial"]:
        problems.append(f"aquifer capacity ({capacity} Mm³) is below the initial stock ({a['initial']} Mm³)")
    if capacity <= a["lowThreshold"]:
        problems.append(f"aquifer capacity ({capacity} Mm³) must be above the low threshold ({a['lowThreshold']} Mm³)")
    worst = worst_case_allocable(scenario, registry)
    if worst <= 0:
        problems.append(
            f"in the worst season the rules allow, no water is left to share ({worst:.3f} Mm³): dry inflow, minus the "
            "largest dry drift and coupling loss, must exceed the reserve"
        )
    return problems


# ---- loading (E2) ------------------------------------------------------------------------------------------------
HA_MM_TO_MM3 = 1e-5  # §2.2 "Area × gross seasonal depth": 1 ha × 1 mm = 10 m³ = 1e-5 Mm³ (unit conversion)
T_PER_MM3_TO_KG_PER_M3 = 1e-3  # §6.1 wpKgM3: 1 t per Mm³ = 1000 kg per 1e6 m³ (unit conversion)
RELATIVE_AGREEMENT = 1e-9  # tolerance: recomputed derived values must agree with the stored ones
EDITABLE_SCHEME_FIELDS = ("areaHa", "depthMm", "beta", "yieldTHa", "ky", "people", "kappa", "price")
SCORING_KEYS = ("r3Ramp", "welfareGamma", "survivalFloor", "welfareSupplyFloor", "sustainabilityBands")


@dataclass(frozen=True)
class ScenarioLoad:
    """The result of loading a scenario: a playable setup, or the reasons it cannot be played."""

    setup: GameSetup | None
    errors: list[str]
    warnings: list[str]


def _schema() -> dict[str, Any]:
    text = resources.files("fairflow_engine").joinpath("scenario.schema.json").read_text(encoding="utf-8")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def _printed_tolerance(value: float) -> float:
    """Half a unit of the last digit the scenario prints (a stored derived value is rounded for display)."""
    text = repr(float(value))
    decimals = len(text.split(".")[1]) if "." in text and "e" not in text else 0
    return 0.5 * 10.0**-decimals  # tolerance: half a unit in the last printed decimal place


def load_scenario(scenario: Mapping[str, Any], registry: Mapping[str, Any]) -> ScenarioLoad:
    """§6.1: validate against the JSON Schema, recompute derived values (they must agree), apply the §5.2 hard checks,
    and build the engine's GameSetup. Parameters the scenario omits come from the registry; nothing is invented."""
    errors: list[str] = []
    warnings: list[str] = []
    validator = Draft202012Validator(_schema())
    for err in sorted(validator.iter_errors(scenario), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"schema: {where}: {err.message}")
    if errors:
        return ScenarioLoad(None, errors, warnings)

    schemes = scenario["schemes"]
    for s in schemes:
        demand = s["areaHa"] * s["depthMm"] * HA_MM_TO_MM3
        capacity = s["areaHa"] * s["yieldTHa"]
        wp = capacity / demand * T_PER_MM3_TO_KG_PER_M3
        d = s["derived"]
        for name, recomputed, stored in (("demandMm3", demand, d["demandMm3"]), ("capacityT", capacity, d["capacityT"])):
            if abs(recomputed - stored) > RELATIVE_AGREEMENT * max(1.0, abs(stored)):
                errors.append(f"scheme {s['id']}: derived.{name} is {stored} but recomputes to {recomputed}")
        if abs(wp - d["wpKgM3"]) > _printed_tolerance(d["wpKgM3"]) + RELATIVE_AGREEMENT:
            errors.append(f"scheme {s['id']}: derived.wpKgM3 is {d['wpKgM3']} but recomputes to {wp}")
        for field in EDITABLE_SCHEME_FIELDS:
            if field not in s.get("fields", {}):
                warnings.append(f"scheme {s['id']}: {field} has no source")
    if len({s["peopleUnit"] for s in schemes}) > 1:
        warnings.append("schemes mix people units (" + ", ".join(sorted({s["peopleUnit"] for s in schemes})) + ") (§6.1)")
    seats = sorted(s["seat"] for s in schemes)
    if seats != list(range(1, len(schemes) + 1)):
        errors.append(f"seats must be 1..{len(schemes)} once each, got {seats}")
    if len({s["id"] for s in schemes}) != len(schemes):
        errors.append("scheme ids must be unique")
    enabled = [lens for lens in scenario["lenses"] if lens["enabled"]]
    if scenario["defaultLens"] not in [lens["id"] for lens in enabled]:
        errors.append(f"defaultLens {scenario['defaultLens']!r} is not an enabled lens")
    length = scenario["basin"]["gameLength"]
    if length["min"] > length["max"]:
        errors.append("gameLength.min exceeds gameLength.max")
    if sum(scenario["basin"]["deck"].values()) < length["max"]:
        errors.append("the deck has fewer cards than the longest game")
    errors.extend(hard_checks(scenario, registry))
    if errors:
        return ScenarioLoad(None, errors, warnings)

    def lens_params(lens: Mapping[str, Any]) -> LensParams:
        prefix = f"lenses.{lens['id']}."
        values = {k[len(prefix) :]: v for k, v in registry.items() if k.startswith(prefix)}
        if lens["id"] == "sufficientarian":  # its prioritarian secondary rule needs the prioritarian parameters
            values = {
                **{k[len("lenses.prioritarian.") :]: v for k, v in registry.items() if k.startswith("lenses.prioritarian.")},
                **values,
            }
        values.update(lens.get("params", {}))
        return LensParams.from_dict(values)

    indicators = scenario.get("indicators", {})
    scoring = Scoring.from_dict({k: indicators.get(k, registry[f"indicators.{k}"]) for k in SCORING_KEYS})
    # review E6: PWF_γ = Σ s^(1−γ)/(1−γ) with s ≥ the supply floor must stay a finite float for every season
    log_worst = math.log(len(schemes)) + (1 - scoring.welfareGamma) * math.log(scoring.welfareSupplyFloor)
    if scoring.welfareGamma > 1 and log_worst >= math.log(sys.float_info.max):
        return ScenarioLoad(None, [f"welfareGamma {scoring.welfareGamma} overflows PWF at the supply floor"], warnings)
    inflow = scenario["basin"]["inflow"]
    setup = GameSetup(
        schemes=tuple(
            Scheme(
                id=s["id"],
                name=s["name"],
                seat=s["seat"],
                demandMm3=s["derived"]["demandMm3"],
                capacityT=s["derived"]["capacityT"],
                ky=s["ky"],
                beta=s["beta"],
                people=s["people"],
                kappa=s["kappa"],
                price=s["price"],
                areaHa=s["areaHa"],
            )
            for s in schemes
        ),
        basin=basin_from_scenario(scenario, registry),
        inflow={card: inflow[card] for card in ("wet", "normal", "dry")},
        deck=dict(scenario["basin"]["deck"]),
        gameLength=(length["min"], length["max"]),
        scoring=scoring,
        lenses=tuple((cast(LensId, lens["id"]), lens_params(lens)) for lens in enabled),
        defaultLens=cast(LensId, scenario["defaultLens"]),
        floorRules=tuple(
            scenario.get("floorRules", sorted(FLOOR_RULES))
        ),  # ADR 0003: all five unless the admin offers fewer
        actions={
            name: {k.split(".")[-1]: v for k, v in registry.items() if k.startswith(f"actions.{name}.")}
            for name in ("orchard", "drip", "expand")
        },
        goals={s["id"]: (s["privateGoal"]["kind"], s["privateGoal"]["threshold"]) for s in schemes},
        authorityMaxMeanPumping=registry["goals.authority.maxMeanPumping"],
        bands={
            "equity": tuple(registry["indicators.equityBands"]),
            "efficiency": tuple(registry["indicators.efficiencyBands"]),
            "adequacy": tuple(registry["indicators.adequacyBands"]),
        },
    )
    return ScenarioLoad(setup, errors, warnings)
