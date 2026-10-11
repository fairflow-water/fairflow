# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Balance harness (blueprint §9.2, ADR 0005 E8): whole games through the authoritative engine, played by strategy
agents, scored against the §9.2 criteria that apply to v1.0 (no modules).

Agents are balance stereotypes, not calibrated humans (§9.2):
- principled:<lens>  votes for the lens and never pumps or plays actions;
- selfish            votes for the lens that gives it the most water this season, pumps the number of tokens that
                     maximises its own points in the engine's private preview (which assumes the others do not pump),
                     and expands its area onto groundwater while pumping pays at the margin and capacity is left
                     (expansion onto groundwater drives real overdraft: Fishman et al. 2015; Shah 2009);
- conditional        votes proportional and pumps selfishly only after a season in which the table pumped.
The Authority proposes every voted lens, breaks ties by the first proposal and lets a floor vote time out ("whatever
works", ADR 0003).

    uv run python analysis/balance.py [games-per-cell] [--set path=value ...]

`--set` overrides a scenario value (dotted path, e.g. basin.aquifer.capacity=24) or a registry default
(registry:actions.pump.cap=3) for calibration runs; overrides are printed with the report.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "engine-py" / "src"))

from fairflow_engine import AUTHORITY, Game, replay  # noqa: E402
from fairflow_engine.scenario import load_scenario  # noqa: E402

SCENARIO = ROOT / "packages" / "scenarios" / "default-basin.json"
REGISTRY = ROOT / "packages" / "scenarios" / "parameters.json"
EPS = 1e-6  # tolerance: the engine rounds water to 1e-6 Mm³ (§7.2)

# §9.2 thresholds, as printed in the blueprint table
LENS_EPJ_RANGE = 0.4  # "dry-year range of E_PJ across lenses ≥ 0.4"
LENS_Q_RANGE = 0.40  # "Q range ≥ 40 % of demand for at least one scheme"
COOP_B_SHARE, COOP_GAMES = 0.5, 0.90  # "all-principled tables end with B_T ≥ 0.5 B₀ in ≥ 90 % of games"
PROFIT_HIGH = 0.80  # "pumping is individually profitable in ≥ 80 % of deficit seasons while B > B_low"
SELFISH_BELOW_LOW = 0.80  # "all-selfish tables drive the water table below … B_low by season 5 in ≥ 80 % of games"
DOMINANT = 0.60  # ADR 0010: "no lens tops the collective score in > 60 % of mixed tables with a defecting seat"
MIXED_GAMES = 400  # ADR 0010: the mixed-game crop-failure rate is reported from at least 400 games
GOALS, GOAL_LENSES = 0.50, 2  # "met in ≥ 50 % of all-principled games … under at least two lenses" (ADR 0008)
CROP_FLOOR_LENS_MIN, CROP_FLOOR_LENS_MAX = 0.05, 0.05  # ADR 0010: some lens ≥ 5 %, some lens ≤ 5 % of its games
Z95 = 1.959964  # two-sided 95 % normal quantile, for the Wilson interval


def scenario_with(overrides: dict[str, Any]) -> tuple[dict, dict]:
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    registry = {p["key"]: p["default"] for p in json.loads(REGISTRY.read_text(encoding="utf-8"))["parameters"]}
    for path, value in overrides.items():
        if path.startswith("registry:"):
            registry[path.removeprefix("registry:")] = value
            continue
        node = scenario
        *keys, last = path.split(".")
        for k in keys:
            node = node[int(k)] if isinstance(node, list) else node[k]
        node[last] = value
    return scenario, registry


def setup_with(overrides: dict[str, Any]) -> Any:
    load = load_scenario(*scenario_with(overrides))
    if load.setup is None:
        raise SystemExit(f"scenario refused: {load.errors}")
    return load.setup


# ---- agents ---------------------------------------------------------------------------------------------------------
def vote_of(strategy: str, role: str, climate: dict, history: list[dict]) -> str:
    if strategy.startswith("principled:"):
        return strategy.split(":", 1)[1]
    if strategy == "selfish":
        i = [x["id"] for x in climate["schemes"]].index(role)
        return max(climate["previews"], key=lambda p: p["Q"][i])["lens"]
    return "proportional"


def action_of(strategy: str, opened: dict, pumps: float) -> str | None:
    """Selfish expansion: Expand when the marginal pump token still pays (pumping one more token raises points) and the
    farm is not already at its pump cap, so the new area can be watered from its own wells."""
    if strategy != "selfish" or "expand" not in opened["actions"]:
        return None
    levels = [(o["pumps"], o["points"]["none"]) for o in opened["options"] if o["points"] is not None]
    i = next((j for j, (k, _) in enumerate(levels) if abs(k - pumps) < EPS), len(levels) - 1)
    pays = i > 0 and levels[i][1] > levels[i - 1][1] + EPS  # the last previewed level taken still raised points
    return "expand" if pays and pumps < opened["cap"] - EPS else None


def pumps_of(strategy: str, opened: dict, history: list[dict]) -> float:
    if strategy.startswith("principled:"):
        return 0.0
    if strategy == "conditional" and not (history and history[-1]["pumpsTotalObserved"] > EPS):
        return 0.0  # reacts to the total the table sees (ADR 0004)
    known = [o for o in opened["options"] if o["points"] is not None]
    best = max(known, key=lambda o: (o["points"]["none"], -o["pumps"]))
    # review E11: above the public limit there is no preview; a selfish farm still pumping profitably at the limit
    # asks for its full capacity and lets the physical rationing decide
    if best is known[-1] and len(known) < len(opened["options"]) and len(known) > 1:
        return float(opened["options"][-1]["pumps"])
    return float(best["pumps"])


# ---- one game -------------------------------------------------------------------------------------------------------
def play(setup: Any, seed: int, table: Sequence[str], force_lens: str | None = None) -> dict[str, Any]:
    """One game. With `force_lens` every seat votes that lens each season; pumping and actions follow each seat's own
    strategy (the counterfactual replay of ADR 0010's "no dominant lens" measure)."""
    roles = [x.id for x in setup.schemes]
    strategy = dict(zip(roles, table, strict=True))
    tick = iter(range(10**7))
    nonce = hashlib.sha256(f"balance-{seed}".encode()).hexdigest()[:32]
    g = Game.create(setup, f"b{seed}", "balance", {"appVersion": "balance", "engineVersion": "balance"},
                    lambda: f"2026-10-08T00:00:{next(tick):07d}Z", nonce)  # fmt: skip
    for r in [*roles, AUTHORITY]:
        g.submit(r, "join", deviceHash=f"balance-{r}", consentGiven=True, presurveyComplete=False)
    history: list[dict] = []
    profit_checks: list[dict] = []
    while replay(g.events).phase != "ended":
        g.submit(AUTHORITY, "start_season")
        climate = g.events[-1]["payload"]
        votes = {r: force_lens or vote_of(strategy[r], r, climate, history) for r in roles}
        for lens in dict.fromkeys(votes.values()):
            g.submit(AUTHORITY, "propose", lens=lens)
        for r in roles:
            g.submit(r, "vote", lens=votes[r])
        g.submit(AUTHORITY, "close_vote")
        if replay(g.events).phase == "tiebreak":  # the Authority breaks a tie by the first leader announced
            tied = next(e["payload"] for e in reversed(g.events) if e["type"] == "lens.tied")
            g.submit(AUTHORITY, "break_tie", lens=tied["leaders"][0])
        if replay(g.events).phase == "floor_vote":
            g.submit(AUTHORITY, "close_floor_vote")
        stock = replay(g.events).stock
        opened = {e["payload"]["role"]: e["payload"] for e in g.events if e["type"] == "private.opened"
                  and e["season"] == climate_season(g)}  # fmt: skip
        for r in roles:
            o = opened[r]
            known = [x for x in o["options"] if x["points"] is not None]
            none = {round(x["pumps"]): x["points"]["none"] for x in known}
            # a deficit season: more water would raise this farm's harvest (pumping one token raises its yield)
            deficit = known[0]["yieldT"] + EPS < max(x["yieldT"] for x in known)
            profitable = none.get(1, none[0]) > none[0] + EPS
            profit_checks.append({"stock": stock, "role": r, "profitable": profitable, "deficit": deficit})
            k = pumps_of(strategy[r], o, history)
            g.submit(r, "commit", pumps=k, action=action_of(strategy[r], o, k))
        resolved = next(e for e in reversed(g.events) if e["type"] == "season.resolved")
        history.append({**resolved["payload"]["public"], "sealed": resolved["payload"]["sealed"]})
    ended = next(e["payload"] for e in g.events if e["type"] == "game.ended")
    goals = {e["payload"]["role"]: e["payload"]["met"] for e in g.events if e["type"] == "goal.result"}
    stocks = [h["sealed"]["stockNext"] for h in history]
    reserve = setup.basin.aquifer.reserve
    at_reserve = next((i + 1 for i, b in enumerate(stocks) if b <= reserve + EPS), None)
    low = setup.basin.aquifer.lowThreshold
    below_low = next((i + 1 for i, b in enumerate(stocks) if b < low - EPS), None)
    return {
        "table": list(table),
        "T": ended["T"],
        "finalStock": stocks[-1],
        "reachedReserveSeason": at_reserve,
        "belowLowSeason": below_low,
        "minStock": min(stocks),
        "collectiveScore": ended["collectiveScore"],
        "cropFailure": ended["cropFailureFlag"],
        "goals": goals,
        "lenses": [e["payload"]["lens"] for e in g.events if e["type"] == "lens.chosen" and e["season"] > 0],
        "spill": sum(h["sealed"]["spill"] for h in history),
        "profitChecks": profit_checks,
    }


def climate_season(g: Game) -> int:
    return next(e["season"] for e in reversed(g.events) if e["type"] == "season.climate")


# ---- the criteria -------------------------------------------------------------------------------------------------
def static_lens_matters(setup: Any) -> dict[str, Any]:
    """'dry-year range of E_PJ across lenses ≥ 0.4; Q range ≥ 40 % of demand for at least one scheme'."""
    from fairflow_engine import resolve_season

    rows = {}
    for lens, params in setup.lenses:  # resolve_season takes the inflow and subtracts the reserve itself
        r = resolve_season(setup.schemes, setup.basin, setup.inflow["dry"], setup.basin.aquifer.initial, lens, params,
                           [0.0] * len(setup.schemes), setup.scoring)  # fmt: skip
        rows[lens] = r
    epj = [r["ePJ"] for r in rows.values()]
    q_range = [
        (max(r["allocation"]["Q"][i] for r in rows.values()) - min(r["allocation"]["Q"][i] for r in rows.values()))
        / s.demandMm3
        for i, s in enumerate(setup.schemes)
    ]
    return {
        "ePJRange": max(epj) - min(epj),
        "qRangeShareMax": max(q_range),
        "pass": max(epj) - min(epj) >= LENS_EPJ_RANGE and max(q_range) >= LENS_Q_RANGE,
    }


def run_cell(args: tuple) -> dict[str, Any]:
    overrides, seed, table, *forced = args
    return play(setup_with(overrides), seed, table, forced[0] if forced else None)


def wilson(k: int, n: int) -> tuple[float, float]:
    """95 % Wilson score interval for k successes in n independent games (one outcome per game)."""
    if n == 0:
        return (0.0, 1.0)
    p, z2 = k / n, Z95 * Z95
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * (p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5 / (1 + z2 / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def report(overrides: dict[str, Any], games: int, workers: int = 8) -> dict[str, Any]:
    setup = setup_with(overrides)
    lenses = [lens for lens, _ in setup.lenses]
    rng = random.Random(20261008)  # seed: fixed so a report is reproducible
    jobs: list[tuple[str, dict, int, tuple[str, ...]]] = []
    for lens in lenses:
        jobs += [(f"principled:{lens}", overrides, k, (f"principled:{lens}",) * 3) for k in range(games)]
    jobs += [("selfish", overrides, k, ("selfish",) * 3) for k in range(games)]
    pool = [*(f"principled:{x}" for x in lenses), "selfish", "conditional"]
    mixed_tables = [tuple(rng.choice(pool) for _ in range(3)) for _ in range(max(games, MIXED_GAMES))]
    jobs += [("mixed", overrides, k, t) for k, t in enumerate(mixed_tables)]
    defecting = [(k, t) for k, t in enumerate(mixed_tables) if "selfish" in t]
    forced_jobs = [(lens, k, t) for k, t in defecting for lens in lenses]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(run_cell, [(o, seed, t) for _, o, seed, t in jobs], chunksize=8))
        forced = list(ex.map(run_cell, [(overrides, k, t, lens) for lens, k, t in forced_jobs], chunksize=8))
    by: dict[str, list[dict]] = {}
    for (cell, *_), r in zip(jobs, results, strict=True):
        by.setdefault(cell, []).append(r)

    principled = [r for c, rs in by.items() if c.startswith("principled:") for r in rs]
    b0 = setup.basin.aquifer.initial
    coop = sum(r["finalStock"] >= COOP_B_SHARE * b0 for r in principled) / len(principled)
    selfish = by["selfish"]
    by5 = sum(r["reachedReserveSeason"] is not None and r["reachedReserveSeason"] <= 5 for r in selfish) / len(selfish)
    not_before3 = sum(r["reachedReserveSeason"] is None or r["reachedReserveSeason"] >= 3 for r in selfish) / len(selfish)
    checks = [c for r in [*selfish, *by["mixed"]] for c in r["profitChecks"] if c["deficit"]]
    low = setup.basin.aquifer.lowThreshold
    high_checks = [c for c in checks if c["stock"] > low]
    profitable_high = sum(c["profitable"] for c in high_checks) / max(1, len(high_checks))
    low_checks = [c for c in checks if c["stock"] < low]
    seats_priced_out = sum(
        1
        for role in [x.id for x in setup.schemes]
        if (rc := [c for c in low_checks if c["role"] == role]) and sum(c["profitable"] for c in rc) / len(rc) < 0.5
    )
    below_low_by5 = sum(r["belowLowSeason"] is not None and r["belowLowSeason"] <= 5 for r in selfish) / len(selfish)
    principled_below = sum(r["belowLowSeason"] is not None for r in principled) / len(principled)
    mixed = by["mixed"]
    tops = Counter(max(set(r["lenses"]), key=r["lenses"].count) for r in mixed)  # most-played lens of each game
    best_by_lens: Counter[str] = Counter()
    for lens in lenses:
        best_by_lens[lens] = sum(r["collectiveScore"] for r in by[f"principled:{lens}"]) / games
    # ADR 0010: the all-principled ranking is the scoreboard's own lens (§2.5), reported, not gated
    principled_top = {}
    for k in range(games):
        scores = {lens: by[f"principled:{lens}"][k]["collectiveScore"] for lens in lenses}
        top = max(scores, key=lambda x: scores[x])
        principled_top[top] = principled_top.get(top, 0) + 1 / games
    # the gated measure: each mixed table with a defecting seat, replayed with each lens forced
    by_table: dict[int, dict[str, float]] = {}
    for (lens, k, _), r in zip(forced_jobs, forced, strict=True):
        by_table.setdefault(k, {})[lens] = r["collectiveScore"]
    forced_top: dict[str, float] = {lens: 0.0 for lens in lenses}
    for scores in by_table.values():
        forced_top[max(scores, key=lambda x: scores[x])] += 1 / max(1, len(by_table))
    goal_rates = {
        role: sum(r["goals"].get(role, False) for r in principled) / len(principled) for role in principled[0]["goals"]
    }
    goals_by_lens = {
        lens: {role: sum(r["goals"].get(role, False) for r in by[f"principled:{lens}"]) / games for role in goal_rates}
        for lens in lenses
    }
    crop_k = sum(r["cropFailure"] for r in mixed)
    crop_by_lens = {lens: sum(r["cropFailure"] for r in by[f"principled:{lens}"]) / games for lens in lenses}
    out = {
        "overrides": overrides,
        "gamesPerCell": games,
        "lensMatters": static_lens_matters(setup),
        "cooperationRewarded": {"share": coop, "pass": coop >= COOP_GAMES},
        "dilemma": {
            "profitableAboveLow": profitable_high,
            "seatsPricedOutBelowLow": seats_priced_out,
            "deficitChecksBelowLow": len(low_checks),
            "selfishReserveBySeason5": by5,
            "selfishNotBeforeSeason3": not_before3,
            "selfishBelowLowBySeason5": below_low_by5,
            "principledEverBelowLow": principled_below,
            "selfishMeanMinStock": sum(r["minStock"] for r in selfish) / len(selfish),
            "pass": profitable_high >= PROFIT_HIGH and below_low_by5 >= SELFISH_BELOW_LOW and principled_below == 0,
        },
        "noDominantLens": {
            "topShareByLens": forced_top,
            "tables": len(by_table),
            "pass": max(forced_top.values()) <= DOMINANT,
            "allPrincipledTop": principled_top,
            "note": "mixed tables with a defecting seat, each replayed with every lens forced (ADR 0010); the "
            "all-principled ranking is the scoreboard's own lens and is reported, not gated",
        },
        "goalsAttainable": {
            "rates": goal_rates,
            "byLens": goals_by_lens,
            "pass": all(sum(g[role] >= GOALS for g in goals_by_lens.values()) >= GOAL_LENSES for role in goal_rates)
            and any(all(v >= GOALS for v in g.values()) for g in goals_by_lens.values()),
        },
        "cropFailure": {
            "byLens": crop_by_lens,
            "mixedShare": crop_k / len(mixed),
            "mixedInterval95": wilson(crop_k, len(mixed)),
            "mixedGames": len(mixed),
            "pass": max(crop_by_lens.values()) >= CROP_FLOOR_LENS_MIN and min(crop_by_lens.values()) <= CROP_FLOOR_LENS_MAX,
            "note": "ADR 0010: some lens leaves a farm below the floor two years running in ≥ 5 % of its all-principled "
            "games and some lens in ≤ 5 %; the mixed-game rate is reported with its 95 % interval",
        },
        "meanFinalStock": {c: sum(r["finalStock"] for r in rs) / len(rs) for c, rs in by.items()},
        "meanSpill": {c: sum(r["spill"] for r in rs) / len(rs) for c, rs in by.items()},
        "mixedLensMostPlayed": dict(tops),
    }
    return out


def main(argv: Sequence[str]) -> None:
    games = int(argv[0]) if argv and argv[0].isdigit() else 50
    overrides: dict[str, Any] = {}
    for i, a in enumerate(argv):
        if a == "--set":
            path, value = argv[i + 1].split("=", 1)
            overrides[path] = json.loads(value)
    print(json.dumps(report(overrides, games), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
