# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Generate, from the authoritative Python engine (ADR 0002):

- packages/engine/fixtures/conformance.json — golden vectors the TypeScript mirror must reproduce: the default basin
  of the blueprint under every card and lens, plus seeded random basins with random parameters and pumping.
  The random draws are test inputs, not model values.
- packages/engine/fixtures/default-basin-beta.json — the §3 β fixture set (β by irrigation method, r₀ = 1).

Run: python scripts/generate_vectors.py   (from packages/engine-py, with the package installed)
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
import blueprint as bp  # noqa: E402  (reads the blueprint; no hand-typed values)
from fairflow_engine import FLOOR_RULES, Basin, LensParams, Scheme, Scoring, resolve_season  # noqa: E402

OUT = bp.FIXTURES
LENSES = ["utilitarian", "weighted_utilitarian", "egalitarian", "proportional", "capability", "sufficientarian",
          "prioritarian", "equal_sacrifice", "talmud"]
SEED = 20261005


def registry_lens_params(lens: str, params: dict) -> dict:
    prefix = f"lenses.{lens}."
    out = {k[len(prefix):]: v for k, v in params.items() if k.startswith(prefix)}
    if lens == "sufficientarian":  # its prioritarian secondary rule needs the prioritarian parameters too
        out.update({k: v for k, v in registry_lens_params("prioritarian", params).items()})
    return out


def scoring_from(params: dict) -> dict:
    return {"r3Ramp": params["indicators.r3Ramp"], "welfareGamma": params["indicators.welfareGamma"],
            "survivalFloor": params["indicators.survivalFloor"], "welfareSupplyFloor": params["indicators.welfareSupplyFloor"],
            "sustainabilityBands": params["indicators.sustainabilityBands"]}


def case(schemes: list[dict], basin: dict, inflow: float, stock: float, lens: str, lens_params: dict,
         pumps: list[float], scoring: dict, label: str) -> dict:
    result = resolve_season([Scheme.from_dict(s) for s in schemes], Basin.from_dict(basin), inflow, stock, lens,
                            LensParams.from_dict(lens_params), pumps, Scoring.from_dict(scoring))
    return {"label": label, "input": {"schemes": schemes, "basin": basin, "inflow": inflow, "stock": stock, "lens": lens,
                                      "lensParams": lens_params, "pumps": pumps, "scoring": scoring},
            "expected": result}


def default_basin_cases(params: dict) -> list[dict]:
    base = bp.basin_v1()
    scoring = scoring_from(params)
    out = []
    for card, inflow in base["inflow"].items():
        for lens in LENSES:
            for pumps in ([0.0, 0.0, 0.0], [params["actions.pump.cap"]] * 3):
                out.append(case(base["schemes"], base["basin"], inflow, base["basin"]["aquifer"]["initial"], lens,
                                registry_lens_params(lens, params), pumps, scoring, f"default {card} {lens} pumps={pumps[0]}"))
    return out


def random_cases(params: dict, n: int) -> list[dict]:
    rng = np.random.default_rng(SEED)
    out = []
    for k in range(n):
        m = int(rng.integers(3, 6))
        schemes = []
        for i in range(m):
            schemes.append({"id": str(i), "name": f"S{i}", "seat": i + 1, "demandMm3": float(rng.uniform(0.5, 12)),
                            "capacityT": float(rng.uniform(300, 8000)), "ky": float(rng.uniform(0.4, 1.4)),
                            "beta": float(rng.uniform(0.4, 1.0)), "people": float(rng.uniform(5, 3000)),
                            "kappa": float(rng.uniform(0.5, 2)), "price": float(rng.uniform(0.3, 3)),
                            "areaHa": float(rng.uniform(50, 1500))})
        b0 = float(rng.uniform(10, 40))
        res = float(rng.uniform(0, 0.3)) * b0
        basin = {"reserve": float(rng.uniform(0, 4)),
                 "aquifer": {"initial": b0, "reserve": res, "lowThreshold": float(rng.uniform(res, b0)),
                             "naturalRecharge": float(rng.uniform(0, 2)),
                             "seatCostMultipliers": sorted(float(x) for x in rng.uniform(1, 3, int(rng.integers(1, 6)))),
                             "maxInflowLossMm3": float(rng.uniform(0, 2)),
                             "tankResolution": float(rng.choice([0.25, 0.5, 1.0, 2.0]))},
                 "pump": {"cap": float(rng.uniform(0.5, 3)), "costBase": float(rng.uniform(0, 4)),
                          "costSlope": float(rng.uniform(0, 10))}}
        demand = sum(s["demandMm3"] for s in schemes)
        inflow = basin["reserve"] + float(rng.uniform(0, 1.3)) * demand
        stock = float(rng.uniform(res, 1.2 * b0))
        lens = LENSES[k % len(LENSES)]
        lp = {"gamma": float(rng.uniform(1, 5)), "weight": str(rng.choice(["1", "people"])),
              "floor": float(rng.uniform(0.2, 0.8)), "floorScaling": str(rng.choice(sorted(FLOOR_RULES))),
              "secondary": str(rng.choice(["max_value", "prioritarian", "proportional"]))}
        pumps = [float(x) for x in rng.uniform(0, basin["pump"]["cap"], m) * (rng.uniform(0, 1, m) < 0.6)]
        g = float(rng.choice([1.0, float(rng.uniform(0.3, 5))]))
        scoring = {"r3Ramp": float(rng.uniform(0.2, 1.2)), "welfareGamma": g,
                   "survivalFloor": float(rng.uniform(0.3, 0.7)), "welfareSupplyFloor": float(rng.uniform(0.001, 0.05)),
                   "sustainabilityBands": sorted(float(x) for x in rng.uniform(0.8, 1.4, 2))}
        out.append(case(schemes, basin, inflow, stock, lens, lp, pumps, scoring, f"random {k} {lens}"))
    return out


def beta_set(params: dict) -> dict:
    """§3: the default basin with β by irrigation method and r₀ from §2.1, no actions, no pumping, B₀."""
    base = bp.basin_v1()
    beta = bp.beta_by_method()
    schemes = [{**s, "beta": float(beta[m])} for s, m in zip(base["schemes"], ["drip", "flood", "sprinkler"])]
    basin = {**base["basin"], "aquifer": {**base["basin"]["aquifer"], "naturalRecharge": float(bp.natural_recharge())}}
    scoring = scoring_from(params)
    out = {"$comment": "SPDX-License-Identifier: CC-BY-4.0 · Blueprint §3 β fixture set, generated by packages/engine-py/scripts/generate_vectors.py from the authoritative Python engine: β by irrigation method and r₀ from §2.1, no actions, no pumping, B₀. Full precision (engine outputs are rounded to 1e-6, §7.2).",
           "generatedBy": "packages/engine-py/scripts/generate_vectors.py", "schemes": schemes, "basin": basin,
           "inflow": base["inflow"], "scoring": scoring}
    for card, inflow in base["inflow"].items():
        out[card] = []
        for lens in LENSES:
            lp = registry_lens_params(lens, params)
            r = resolve_season([Scheme.from_dict(s) for s in schemes], Basin.from_dict(basin), inflow,
                               basin["aquifer"]["initial"], lens, LensParams.from_dict(lp), [0.0] * 3, Scoring.from_dict(scoring))
            out[card].append({"lens": lens, "lensParams": lp, "expected": r})
    return out


def jsonable(x):
    return float(x) if isinstance(x, (np.floating, bp.Num)) else x


def write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, default=jsonable, separators=(",", ":")) + "\n", encoding="utf-8")


def build() -> tuple[dict, dict]:
    params = bp.registry()  # the shipped defaults, no fixture overrides
    vectors = {"$comment": "SPDX-License-Identifier: CC-BY-4.0 · Golden vectors from the authoritative Python engine (ADR 0002). The TypeScript mirror must reproduce every `expected` within the §7.2 rounding. Random inputs are test draws, not model values.",
               "generatedBy": "packages/engine-py/scripts/generate_vectors.py", "seed": SEED,
               "cases": default_basin_cases(params) + random_cases(params, 400)}
    return vectors, beta_set(params)


if __name__ == "__main__":
    vectors, beta = build()
    write(OUT / "conformance.json", vectors)
    write(OUT / "default-basin-beta.json", beta)
    print(f"wrote {len(vectors['cases'])} conformance cases and the β set to {OUT}")
