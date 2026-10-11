# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The ADR 0004 feasibility audit: how much does what the table sees during play reveal about each farm's pumping?

For each test season, every pumping vector the private turn could have produced is resolved with the engine's own
`resolve_season` and compared with the true one on what a display shows; the candidates that match form the observer's
feasible set. The scenario is the shipped one (`packages/scenarios/default-basin.json`, loaded with `load_scenario` and
the parameter registry), so caps, dry wells, costs and the aquifer balance are the engine's. This script implements no
equation.

Observers
- outsider: knows the scenario, the public allocation and the stock at the start of the season (conservative: the table
  sees only the coarse level);
- insider: another farm, which also knows its own request and sees its own `self` payload of `season.resolved` as
  `record.project` gives it (pumpCost, P, W, A, Y, dL; points and L follow from dL, no actions are modelled).
  A farm counts as identified by insiders if at least one of the other two farms can identify it.

Displays
- implemented: `record.PUBLIC_RESULT_FIELDS` (the observed total, at the tank resolution, since 2026-10-11);
- floor: the observed total only (what any commons game with a public total at this resolution shows);
- for reference, the previous display (the same fields with the exact total) and its floor (the exact total only).

Measures, per farm and season: "identified" (all feasible candidates agree within 0.1 Mm³) and "knows whether pumped"
(all agree on pumping > 0). A farm whose wells are dry (cap 0, which the table knows from the observed level) is a
structurally known zero; "pumpable" rows drop it.

Statistics. The season is the sampling unit: stock, card, lens and the pumping vector are drawn once per season and the
three farms share one feasible set, so farm-seasons are not independent. Reported: per farm, a Wilson interval with
n = seasons; pooled, a cluster bootstrap over seasons; season level, "any farm identified" with a Wilson interval; and
the paired cluster-bootstrap difference implemented − floor on the same seasons.

Release gate (ADR 0004 item 5, restated 2026-10-12): on the private turn's action space, at 1,000 seasons per stock
regime, the upper 95 % bound of the paired difference implemented − floor, over pumpable farms, must not exceed
5 points for "identified" (margin: maintainer convention, to be confirmed) and 12 points for "knows whether pumped".

    uv run python analysis/privacy_leakage.py                 # private-turn levels, 1,000 seasons per regime, gate
    uv run python analysis/privacy_leakage.py --grid [N]      # also the 0.1 Mm³ grid sensitivity run (N seasons)
"""

from __future__ import annotations

import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "engine-py" / "src"))

import fairflow_engine.season as _season  # noqa: E402
from fairflow_engine import resolve_season  # noqa: E402
from fairflow_engine.aquifer import inflow_loss_next, pump_cap  # noqa: E402
from fairflow_engine.record import PUBLIC_RESULT_FIELDS  # noqa: E402
from fairflow_engine.scenario import load_scenario  # noqa: E402

SCENARIO = ROOT / "packages" / "scenarios" / "default-basin.json"
REGISTRY = ROOT / "packages" / "scenarios" / "parameters.json"

SEED = 20261012  # analysis setting
SEASONS = 1000  # analysis setting: seasons per stock regime for the gate (400 left the gate sensitive to resampling)
GRID_SEASONS = 300  # analysis setting: the 0.1 Mm³ grid run is a sensitivity run (about 27,000 candidates a season)
GRID_STEP = 0.1  # analysis setting: Mm³
IDENTIFIED = 0.1  # analysis setting: identified if all consistent candidates agree within this (Mm³)
P_PUMPS = 0.6  # analysis setting: chance a farm pumps in a test season (then uniform over its levels), as before
BOOTSTRAP = 10_000  # analysis setting: cluster-bootstrap resamples
GATE = {"identified": 5.0, "knows whether pumped": 12.0}  # points; 5 is a maintainer convention to be confirmed
SELF_KEYS = ("pumpCost", "P", "W", "A", "Y", "dL")  # the per-farm fields record.project puts in a player's `self`
EXACT = {"pumpsTotalObserved": "pumpsTotal"}  # the display before 2026-10-11 showed the exact total
MEASURES = ("outsider identified", "outsider knows whether pumped", "insider identified", "insider knows whether pumped")
DISPLAYS = {
    "implemented": lambda r: repr({f: r[f] for f in PUBLIC_RESULT_FIELDS}),
    "floor": lambda r: repr(r["pumpsTotalObserved"]),
    "previous (exact total)": lambda r: repr({f: r[EXACT.get(f, f)] for f in PUBLIC_RESULT_FIELDS}),
    "previous floor (exact total)": lambda r: repr(r["pumpsTotal"]),
}
PAIRS = (("implemented", "floor"), ("previous (exact total)", "previous floor (exact total)"))


def _setup() -> Any:
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    registry = {p["key"]: p["default"] for p in json.loads(REGISTRY.read_text(encoding="utf-8"))["parameters"]}
    load = load_scenario(scenario, registry)
    if load.setup is None:
        raise SystemExit(f"scenario refused: {load.errors}")
    return load.setup


SETUP = _setup()
SCHEMES, BASIN, SCORING, LENSES = SETUP.schemes, SETUP.basin, SETUP.scoring, SETUP.lenses

_allocate = _season.allocate
_allocations: dict[tuple, Any] = {}


def _cached_allocate(lens, schemes, allocable, params, floor):
    """The allocation does not depend on pumping; computing it once per season keeps the enumeration fast."""
    key = (lens, allocable, tuple(id(s) for s in schemes), id(params), floor)
    if key not in _allocations:
        _allocations[key] = _allocate(lens, schemes, allocable, params, floor)
    return _allocations[key]


_season.allocate = _cached_allocate


def levels(stock: float, scheme: Any, space: str) -> list[float]:
    """The pump levels a farm can choose: the private turn offers whole tokens 0..⌊cap⌋ and a fractional cap as its own
    last level (record._open_private_turns); the grid run uses 0.1 Mm³ steps up to the cap."""
    cap = pump_cap(BASIN, stock, scheme)
    if space == "tokens":
        out = [float(k) for k in range(int(cap) + 1)]
    else:
        out = [round(GRID_STEP * k, 6) for k in range(int(round(cap / GRID_STEP, 6)) + 1)]
    if cap > out[-1] + 1e-9:  # tolerance: caps are rounded to 1e-6 Mm³ (§7.2)
        out.append(cap)
    return out


def season(args: tuple[int, str, str]) -> dict[str, Any]:
    """One test season: the outcome of every measure for every farm under every display."""
    k, space, regime = args
    rng = np.random.default_rng([SEED, k, int(regime == "upper"), int(space == "tokens")])
    card = ["dry", "normal", "wet"][k % 3]
    lens, params = LENSES[k % len(LENSES)]
    aq = BASIN.aquifer
    low, high = (aq.lowThreshold, aq.initial) if regime == "upper" else (aq.reserve, aq.lowThreshold)
    stock = float(rng.uniform(low, high))
    inflow = SETUP.inflow[card] - inflow_loss_next(BASIN, stock)  # this season's inflow after the baseflow loss
    options = [levels(stock, s, space) for s in SCHEMES]
    truth_p = tuple(float(rng.choice(o)) if rng.uniform() < P_PUMPS else 0.0 for o in options)
    candidates = list(itertools.product(*options))
    results = {c: resolve_season(SCHEMES, BASIN, inflow, stock, lens, params, list(c), SCORING) for c in candidates}
    truth = results[truth_p]
    grid = np.array(candidates)
    n = len(SCHEMES)
    own = [  # what farm j sees privately: its own request and its own `self` payload
        np.isclose(grid[:, j], truth_p[j])
        & np.array([all(results[c][key][j] == truth[key][j] for key in SELF_KEYS) for c in candidates])
        for j in range(n)
    ]
    outcomes = {}
    for name, show in DISPLAYS.items():
        seen = show(truth)
        match = np.array([show(results[c]) == seen for c in candidates])
        row = np.zeros((len(MEASURES), n), dtype=bool)
        for i in range(n):
            col = grid[match][:, i]
            row[0, i] = np.ptp(col) <= IDENTIFIED
            row[1, i] = len(set(col > 0)) == 1
            for j in range(n):
                if j != i:
                    sub = grid[match & own[j]][:, i]
                    row[2, i] |= np.ptp(sub) <= IDENTIFIED
                    row[3, i] |= len(set(sub > 0)) == 1
        outcomes[name] = row
    return {
        "outcomes": outcomes,
        "pumpable": np.array([pump_cap(BASIN, stock, s) > 0 for s in SCHEMES]),
        "rationed": sum(truth_p) > max(0.0, stock - aq.reserve) + 1e-9,  # tolerance: water rounded to 1e-6 Mm³
    }


def wilson(k: int, n: int) -> tuple[float, float]:
    """95 % Wilson score interval for a proportion (scipy.stats.binomtest)."""
    from scipy.stats import binomtest

    if n == 0:
        return float("nan"), float("nan")
    ci = binomtest(int(k), int(n)).proportion_ci(confidence_level=0.95, method="wilson")
    return ci.low, ci.high


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def report(rows: list[dict[str, Any]], title: str, gate: bool) -> list[str]:
    seasons = len(rows)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, seasons, size=(BOOTSTRAP, seasons))
    pumpable = np.stack([r["pumpable"] for r in rows])  # seasons × farms
    every = np.ones_like(pumpable)
    data = {d: np.stack([r["outcomes"][d] for r in rows]) for d in DISPLAYS}  # seasons × measures × farms
    names = [s.id for s in SCHEMES]
    out = [
        f"### {title}",
        "",
        f"{seasons} seasons; pumping rationed in {sum(r['rationed'] for r in rows)}; farm "
        f"{names[int(np.argmin(pumpable.sum(axis=0)))]} unable to pump (dry wells) in "
        f"{int((~pumpable).any(axis=1).sum())}.",
        "",
    ]

    def pooled(x: np.ndarray, w: np.ndarray) -> tuple[float, float, float]:
        num, den = (x * w).sum(axis=1), w.sum(axis=1)  # per season
        boot = num[idx].sum(axis=1) / den[idx].sum(axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        return num.sum() / den.sum(), lo, hi

    for label, weight in (("all farms", every), ("pumpable farms only (dry wells dropped)", pumpable)):
        out += [
            f"**{label}**",
            "",
            "| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm "
            + "/".join(names)
            + " % (Wilson, n = seasons) | Any farm, season level % (Wilson) |",
            "|---|---|---|---|---|",
        ]
        for d, x in data.items():
            for m, measure in enumerate(MEASURES):
                xm = x[:, m, :]
                p, lo, hi = pooled(xm, weight)
                farms = []
                for i in range(len(names)):
                    ok = weight[:, i]
                    k, n = int(xm[ok, i].sum()), int(ok.sum())
                    a, b = wilson(k, n)
                    farms.append(f"{pct(k / n)} ({pct(a)}–{pct(b)})" if n else "—")
                hit = (xm & weight).any(axis=1)
                a, b = wilson(int(hit.sum()), seasons)
                out.append(
                    f"| {d} | {measure} | {pct(p)} ({pct(lo)}–{pct(hi)}) | {' / '.join(farms)} | "
                    f"{pct(hit.mean())} ({pct(a)}–{pct(b)}) |"
                )
        out.append("")

    out += [
        "**Paired difference, display − its floor, pumpable farms (cluster bootstrap 95 %)**",
        "",
        "| Display vs floor | Measure | Difference, points | Upper 95 % | Gate margin | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for shown, floor in PAIRS:
        for m, measure in enumerate(MEASURES):
            a, f = (data[shown][:, m, :] & pumpable), (data[floor][:, m, :] & pumpable)
            diff = (a.astype(float) - f).sum(axis=1)
            den = pumpable.sum(axis=1)
            boot = diff[idx].sum(axis=1) / den[idx].sum(axis=1)
            lo, hi = np.percentile(boot, [2.5, 97.5])
            margin = GATE["identified" if measure.endswith("identified") else "knows whether pumped"]
            verdict = ("PASS" if 100 * hi <= margin else "FAIL") if gate and shown == "implemented" else "(reference)"
            out.append(
                f"| {shown} vs {floor} | {measure} | {100 * diff.sum() / den.sum():+.1f} ({100 * lo:+.1f} to "
                f"{100 * hi:+.1f}) | {100 * hi:+.1f} | ≤ {margin:g} | {verdict} |"
            )
    out.append("")
    return out


def run(space: str, regime: str, seasons: int) -> list[dict[str, Any]]:
    with ProcessPoolExecutor() as pool:
        return list(pool.map(season, [(k, space, regime) for k in range(seasons)], chunksize=4))


def main() -> None:
    grid = "--grid" in sys.argv
    tail = sys.argv[sys.argv.index("--grid") + 1 :] if grid else []
    grid_seasons = int(tail[0]) if tail and tail[0].isdigit() else GRID_SEASONS
    regimes = {
        "upper": f"B_low to B₀ ({BASIN.aquifer.lowThreshold:g}–{BASIN.aquifer.initial:g} Mm³)",
        "lower": f"B_res to B_low ({BASIN.aquifer.reserve:g}–{BASIN.aquifer.lowThreshold:g} Mm³)",
    }
    lines = []
    for regime, label in regimes.items():
        lines += report(run("tokens", regime, SEASONS), f"Private-turn levels, stock {label} — release gate", True)
    if grid:
        for regime, label in regimes.items():
            lines += report(run("grid", regime, grid_seasons), f"0.1 Mm³ grid, stock {label} — sensitivity", False)
    lines.append(
        f"Seed {SEED}; a farm pumps with probability {P_PUMPS}, uniformly over its levels; identified = all consistent "
        f"candidates within {IDENTIFIED} Mm³; {BOOTSTRAP} cluster-bootstrap resamples over seasons; gate margins "
        f"{GATE['identified']:g} points (identified, maintainer convention to confirm) and "
        f"{GATE['knows whether pumped']:g} points (knows whether pumped)."
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
