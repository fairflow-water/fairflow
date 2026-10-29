# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0017 decision 6: the basin game must not change while scheme mode is built. Write a small, fixed set of whole
games on the shipped Kelvara scenario (default-basin), played by the balance harness's strategies, to
packages/engine/fixtures/default-basin-guard.json. tests/test_regression_guard.py replays them on every PR and fails
on any difference, alongside the conformance vectors (generate_vectors.py) and the UI fixtures (generate_ui_fixture.py).

Run: python scripts/generate_regression_guard.py   (from packages/engine-py)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "analysis"))
import balance  # noqa: E402

OUT = HERE.parents[2] / "packages" / "engine" / "fixtures" / "default-basin-guard.json"
SEEDS = (0, 2)  # guard input: two seeds per table, chosen so the guard holds a game of each length (T = 5 and T = 6)
MIXED = (  # guard input: tables mixing the harness's strategies, one with a defecting seat
    ("principled:proportional", "selfish", "conditional"),
    ("conditional", "conditional", "conditional"),
)


def tables(setup: Any) -> list[tuple[str, ...]]:
    """Each enabled lens played by three principled seats, an all-selfish table, then the mixed tables."""
    lenses = [lens for lens, _ in setup.lenses]
    return [*((f"principled:{lens}",) * 3 for lens in lenses), ("selfish",) * 3, *MIXED]


def build() -> dict[str, Any]:
    setup = balance.setup_with({})
    games = [balance.play(setup, seed, table) for table in tables(setup) for seed in SEEDS]
    return {
        "generatedBy": "packages/engine-py/scripts/generate_regression_guard.py",
        "scenario": "default-basin",
        "seeds": list(SEEDS),
        "games": games,
    }


def main() -> None:
    text = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    OUT.write_text(text, encoding="utf-8", newline="\n")  # LF on every platform
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
