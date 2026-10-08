# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""§5.2 hard checks on the shipped scenario and on deliberately broken copies (the breakages are test inputs)."""

import copy
import json

from blueprint import ROOT, registry

from fairflow_engine.scenario import hard_checks, worst_case_allocable

DEFAULT = json.loads((ROOT / "packages" / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))
REG = registry()


def broken(**changes):
    s = copy.deepcopy(DEFAULT)
    for path, value in changes.items():
        node = s
        *keys, last = path.split("__")
        for k in keys:
            node = node[k]
        node[last] = value
    return s


def test_shipped_default_basin_passes():
    assert hard_checks(DEFAULT, REG) == []
    assert worst_case_allocable(DEFAULT, REG) > 0


def test_reserve_at_or_above_dry_inflow_is_refused():
    s = broken(basin__reserve__value=DEFAULT["basin"]["inflow"]["dry"])
    assert any("must be below the dry inflow" in p for p in hard_checks(s, REG))


def test_no_scarcity_is_refused():
    total = sum(x["derived"]["demandMm3"] for x in DEFAULT["schemes"])
    s = broken(basin__inflow__dry=total + DEFAULT["basin"]["reserve"]["value"])
    assert any("no scarcity" in p for p in hard_checks(s, REG))


def test_worst_season_without_water_is_refused():
    """Large coupling loss or dry drift can empty the worst season even when the plain dry year has water."""
    margin = worst_case_allocable(DEFAULT, REG)
    s = broken(basin__inflow__dryDrift=(margin + 1) / DEFAULT["basin"]["gameLength"]["max"])
    assert any("no water is left to share" in p for p in hard_checks(s, REG))


def test_aquifer_capacity_below_start_or_low_threshold_is_refused():
    """ADR 0006: the aquifer cannot start above its capacity, and a capacity at B_low leaves no room above it."""
    a = DEFAULT["basin"]["aquifer"]
    assert any("below the initial stock" in p for p in hard_checks(broken(basin__aquifer__capacity=a["initial"] / 2), REG))
    low = broken(basin__aquifer__capacity=a["lowThreshold"])
    assert any("above the low threshold" in p for p in hard_checks(low, REG))


def test_aquifer_starting_below_its_reserve_is_refused():
    """Review E2: below B_res the §2.6 floor max(B_res, ·) would add water that never entered the basin."""
    a = DEFAULT["basin"]["aquifer"]
    problems = hard_checks(broken(basin__aquifer__initial=a["reserve"] / 2), REG)
    assert any("below its reserve" in p for p in problems)


def test_capacity_defaults_to_the_registry_value_and_the_initial_stock():
    """ADR 0006: the shipped capacity is the registry default, which equals B0; a scenario that omits it is full at
    the start."""
    load = load_scenario(DEFAULT, REG)
    assert load.setup is not None
    assert load.setup.basin.aquifer.capacity == REG["basin.aquifer.capacity"] == DEFAULT["basin"]["aquifer"]["initial"]
    s = copy.deepcopy(DEFAULT)
    del s["basin"]["aquifer"]["capacity"]
    omitted = load_scenario(s, REG).setup
    assert omitted is not None
    assert omitted.basin.aquifer.capacity == s["basin"]["aquifer"]["initial"]


def test_fraction_reserve_is_refused_until_supported():
    s = broken(basin__reserve__mode="fraction")
    assert hard_checks(s, REG) == ["reserve.mode 'fraction' is not supported yet; give the reserve in Mm³"]


# ---- loader (E2) ----------------------------------------------------------------------------------------------------
import blueprint as bp  # noqa: E402

from fairflow_engine import AUTHORITY, Game, audit, replay  # noqa: E402
from fairflow_engine.scenario import load_scenario  # noqa: E402


def test_shipped_scenario_loads_into_the_blueprint_basin():
    """The default scenario must give exactly the §2.1–2.2 basin, with the shipped β by method (values read from the
    blueprint text, not typed here)."""
    load = load_scenario(DEFAULT, REG)
    assert load.errors == []
    assert load.setup is not None
    want = bp.basin_v1()
    beta = bp.beta_by_method()
    for got, w, method in zip(load.setup.schemes, want["schemes"], ["drip", "flood", "sprinkler"], strict=True):
        for key in ("demandMm3", "capacityT", "ky", "people", "areaHa", "kappa", "price"):
            assert getattr(got, key) == w[key], (got.id, key)
        assert got.beta == beta[method]
    assert load.setup.basin.reserve == want["basin"]["reserve"]
    assert load.setup.inflow == want["inflow"]
    assert [lens for lens, _ in load.setup.lenses] == [
        "utilitarian",
        "egalitarian",
        "proportional",
        "capability",
        "sufficientarian",
    ]


def test_shipped_scenario_warnings_are_the_open_source_gaps():
    """Missing sources and the mixed people unit are reported (warnings now; a release gate under §1.5)."""
    warnings = load_scenario(DEFAULT, REG).warnings
    assert "scheme A: areaHa has no source" in warnings
    assert any("mix people units" in w for w in warnings)
    assert "scheme C: yieldTHa has no source" not in warnings


def test_a_loaded_scenario_plays_and_audits():
    setup = load_scenario(DEFAULT, REG).setup
    assert setup is not None
    tick = iter(range(10**6))
    g = Game.create(setup, "loaded", "room", {"appVersion": "test"}, lambda: f"t{next(tick)}", "a" * 32)
    for role in [*(s.id for s in setup.schemes), AUTHORITY]:
        g.submit(role, "join", deviceHash=role, consentGiven=True, presurveyComplete=True)
    while replay(g.events).phase != "ended":
        g.submit(AUTHORITY, "start_season")
        g.submit(AUTHORITY, "close_vote")  # timer expiry: the default lens, then the previous one (R8)
        for s in setup.schemes:
            g.submit(s.id, "commit", pumps=0.0)
    assert audit(setup, g.events) == []


def test_derived_values_must_agree():
    s = broken()
    s["schemes"][2]["yieldTHa"] = 5.88  # the earlier rounded copy: 340 × 5.88 ≠ 2000
    assert any("derived.capacityT" in e for e in load_scenario(s, REG).errors)


def test_schema_and_consistency_errors_name_the_problem():
    unknown = broken()
    unknown["surprise"] = 1
    assert any(e.startswith("schema: (root)") for e in load_scenario(unknown, REG).errors)
    bad_lens = broken()
    bad_lens["lenses"][0]["id"] = "fairest"
    assert any("schema: lenses/0/id" in e for e in load_scenario(bad_lens, REG).errors)
    disabled_default = broken()
    for lens in disabled_default["lenses"]:
        if lens["id"] == disabled_default["defaultLens"]:
            lens["enabled"] = False
    assert any("is not an enabled lens" in e for e in load_scenario(disabled_default, REG).errors)
    short_deck = broken(basin__deck={"wet": 1, "normal": 1, "dry": 1})
    assert any("fewer cards than the longest game" in e for e in load_scenario(short_deck, REG).errors)
