# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""How much does each candidate in-play display reveal about individual pumping? (supports ADR 0004)

For each test season, every pumping vector on a grid is checked against what the display shows; the candidates that
match form the observer's feasible set. An outsider knows the scenario and the public allocation; an insider also
knows their own pumping. All indicators are computed with the engine's own functions; this script implements no
equation. Band edges come from the parameter registry. Grid step, season count and tank resolutions are analysis
settings, not model values.

Run: python analysis/privacy_leakage.py   (prints a Markdown table)
"""

from __future__ import annotations

import itertools
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
import blueprint as bp  # noqa: E402
from fairflow_engine import (allocate, efficiency, equity_pj, equity_se, LensParams, next_stock,  # noqa: E402
                             return_flow, Scheme, Basin, sustainability)

GRID_STEP = 0.1          # analysis setting: resolution of the candidate grid (Mm³)
SEASONS = 45             # analysis setting
IDENTIFIED = 0.1         # analysis setting: a scheme's pumping counts as identified if all candidates agree within this

params = bp.registry()
base = bp.basin_v1()
beta = bp.beta_by_method()
SCHEMES = [replace(Scheme.from_dict(s), beta=float(beta[m])) for s, m in zip(base["schemes"], ["drip", "flood", "sprinkler"])]
BASIN = Basin.from_dict({**base["basin"], "aquifer": {**base["basin"]["aquifer"], "naturalRecharge": float(bp.natural_recharge())}})
FLOOR = params["indicators.survivalFloor"]
BANDS = {"equity": params["indicators.equityBands"], "efficiency": params["indicators.efficiencyBands"],
         "sustainability": params["indicators.sustainabilityBands"]}
CAP = BASIN.pump.cap
LENSES = ["proportional", "utilitarian", "egalitarian", "capability", "equal_sacrifice"]


def lens_params(lens):
    prefix = f"lenses.{lens}."
    return LensParams(**{k[len(prefix):]: v for k, v in params.items() if k.startswith(prefix)})


def band(x, edges):
    return int(np.searchsorted(edges, x, side="right"))


def actual(Q, P, allocable, stock, surplus):
    """Engine indicators on actual water use W = Q + P."""
    W = [q + p for q, p in zip(Q, P)]
    return {"ePJ": equity_pj(SCHEMES, W), "eSE": equity_se(SCHEMES, W, "claimant"),
            "F": efficiency(SCHEMES, W, "consumed", FLOOR), "S": sustainability(SCHEMES, W, allocable, BASIN.aquifer.naturalRecharge),
            "stock": next_stock(BASIN, stock, surplus, return_flow(SCHEMES, W), sum(P))}


def displays(Q, P, allocable, stock, surplus):
    """What each candidate design puts on the shared screen (beyond the public allocation Q)."""
    a = actual(Q, P, allocable, stock, surplus)
    total = round(sum(P), 6)
    bands = (band(a["ePJ"], BANDS["equity"]), band(a["eSE"], BANDS["equity"]),
             band(a["F"], BANDS["efficiency"]), band(a["S"], BANDS["sustainability"]))
    exact = tuple(round(a[k], 6) for k in ("ePJ", "eSE", "F", "S"))
    return {
        "A. §6.2 as written: exact actual-use dials, exact tank, ΣP": (total, round(a["stock"], 6), exact),
        "B. ΣP + exact tank (dials on allocation only)": (total, round(a["stock"], 6)),
        "C. ΣP + tank to 1 Mm³": (total, int(a["stock"] // 1)),
        "D. ΣP + tank to 2 Mm³": (total, int(a["stock"] // 2)),
        "E. ΣP only (no tank)": (total,),
        "F. ΣP + actual-use band words (no tank)": (total, bands),
        "G. ΣP + tank to 1 Mm³ + actual-use band words": (total, int(a["stock"] // 1), bands),
        "H. ΣP + exact tank + actual-use band words": (total, round(a["stock"], 6), bands),
        "I. ΣP + tank to 1 Mm³ + sustainability band only": (total, int(a["stock"] // 1), bands[3]),
        "J. ΣP + tank to 1 Mm³ + equity bands only": (total, int(a["stock"] // 1), bands[0:2]),
        "K. ΣP + tank to 1 Mm³ + efficiency band only": (total, int(a["stock"] // 1), bands[2]),
    }


def main():
    rng = np.random.default_rng(20261005)  # analysis setting
    grid = np.round(np.arange(0, CAP + 1e-9, GRID_STEP), 6)
    candidates = [tuple(c) for c in itertools.product(grid, repeat=len(SCHEMES))]
    stats = {}
    for k in range(SEASONS):
        card = ["dry", "normal", "wet"][k % 3]
        lens = LENSES[k % len(LENSES)]
        inflow = base["inflow"][card]
        allocable = max(0.0, inflow - BASIN.reserve)
        alloc = allocate(lens, SCHEMES, allocable, lens_params(lens), FLOOR)
        stock = float(rng.uniform(BASIN.aquifer.lowThreshold, BASIN.aquifer.initial))
        true_P = tuple(float(rng.choice(grid)) if rng.uniform() < 0.6 else 0.0 for _ in SCHEMES)
        observed = displays(alloc.Q, true_P, allocable, stock, alloc.surplusToAquifer)
        signatures = [displays(alloc.Q, c, allocable, stock, alloc.surplusToAquifer) for c in candidates]
        for design, obs in observed.items():
            feasible = np.array([c for c, sig in zip(candidates, signatures) if sig[design] == obs])
            s = stats.setdefault(design, {"out_id": 0, "out_who": 0, "in_id": 0, "in_who": 0, "n": 0})
            s["n"] += len(SCHEMES)
            for i in range(len(SCHEMES)):
                col = feasible[:, i]
                s["out_id"] += np.ptp(col) <= IDENTIFIED
                s["out_who"] += len(set(col > 0)) == 1
                # insider: scheme j ≠ i knows its own pumping; count i identified/who-pumped by at least one insider
                ins_id = ins_who = False
                for j in range(len(SCHEMES)):
                    if j == i:
                        continue
                    sub = feasible[np.isclose(feasible[:, j], true_P[j])][:, i]
                    ins_id |= np.ptp(sub) <= IDENTIFIED
                    ins_who |= len(set(sub > 0)) == 1
                s["in_id"] += ins_id
                s["in_who"] += ins_who
    print("| In-play display | Outsider: pumping identified | Outsider: knows whether pumped | Insider: identified | Insider: knows whether pumped |")
    print("|---|---|---|---|---|")
    for design, s in stats.items():
        pct = lambda x: f"{100 * x / s['n']:.0f} %"
        print(f"| {design} | {pct(s['out_id'])} | {pct(s['out_who'])} | {pct(s['in_id'])} | {pct(s['in_who'])} |")
    print(f"\n{SEASONS} seasons × {len(SCHEMES)} schemes; grid {GRID_STEP} Mm³ (0..{CAP}); identified = all consistent "
          f"candidates within {IDENTIFIED} Mm³; insider = another player who knows their own pumping.")


if __name__ == "__main__":
    main()
