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


def test_fraction_reserve_is_refused_until_supported():
    s = broken(basin__reserve__mode="fraction")
    assert hard_checks(s, REG) == ["reserve.mode 'fraction' is not supported yet; give the reserve in Mm³"]
