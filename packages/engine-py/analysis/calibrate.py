# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Calibration of the Kelvara basin's teaching conventions against the §9.2 balance criteria (ADR 0007).

Only values that the scenario and ADR 0007 label as conventions are searched: aquifer storage and its thresholds, the
pump-cost curve, seat multipliers, the pump cap. Sourced values (crops, prices, people, inflows, reserve, recharge,
consumed fractions, the return-flow recharge share) are held fixed. Every candidate is played by the balance harness
(`balance.py`); the report lists, for each candidate, which criteria pass, so the choice is made in the open.

    uv run python analysis/calibrate.py [games-per-cell]
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from balance import report

# The grid: storage B₀ (= capacity, ADR 0006) with B_res and B_low as fixed shares of it, the cost slope, the seat
# multipliers and the cap. Shares 0.25 and 0.5 keep the blueprint's proportions B_res/B₀ = 5/20, B_low/B₀ = 10/20.
STORAGE = [12, 16, 20]
COST_SLOPE = [6, 10, 14]
SEATS = [[1.0, 1.5, 2.0], [1.0, 2.0, 3.0]]
CAP = [2, 3]


def candidates() -> list[dict]:
    out = []
    for b0, slope, seats, cap in itertools.product(STORAGE, COST_SLOPE, SEATS, CAP):
        out.append(
            {
                "basin.aquifer.initial": b0,
                "basin.aquifer.capacity": b0,
                "basin.aquifer.reserve": b0 * 0.25,
                "basin.aquifer.lowThreshold": b0 * 0.5,
                "basin.aquifer.seatCostMultipliers": seats,
                "registry:actions.pump.costSlope": slope,
                "registry:actions.pump.cap": cap,
            }
        )
    return out


def main(argv: list[str]) -> None:
    games = int(argv[0]) if argv else 20
    rows = []
    for c in candidates():
        r = report(c, games)
        passed = {k: v["pass"] for k, v in r.items() if isinstance(v, dict) and "pass" in v}
        rows.append({"overrides": c, "passed": passed, "score": sum(passed.values()), "dilemma": r["dilemma"],
                     "goals": r["goalsAttainable"]["rates"], "crop": r["cropFailureMixed"]["share"],
                     "coop": r["cooperationRewarded"]["share"]})  # fmt: skip
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    best = max(rows, key=lambda x: x["score"])
    print("BEST", json.dumps(best, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
