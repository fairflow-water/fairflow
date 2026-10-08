# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Read the §3 reference vectors directly from docs/blueprint.md, so expected values come from the blueprint text,
never from a hand-typed copy."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLUEPRINT = (ROOT / "docs" / "blueprint.md").read_text(encoding="utf-8")
FIXTURES = ROOT / "packages" / "engine" / "fixtures"

# Row labels in the §3 tables → lens ids. Labels carry notes ("(κ = 1)", "(= Talmud here)"); the leading words decide.
LABELS = [
    ("Weighted utilitarian", "weighted_utilitarian"),
    ("Utilitarian", "utilitarian"),
    ("Strict egalitarian", "egalitarian"),
    ("Proportional", "proportional"),
    ("Capability", "capability"),
    ("Sufficientarian", "sufficientarian"),
    ("Prioritarian", "prioritarian"),
    ("Equal sacrifice", "equal_sacrifice"),
    ("Talmud", "talmud"),
]


class Num(float):
    """A number as printed in the blueprint; `tol` is half a unit of its last printed digit."""

    tol: float

    def __new__(cls, text: str) -> Num:
        clean = text.strip().replace(",", "").replace("−", "-")
        obj = super().__new__(cls, float(clean))
        decimals = len(clean.split(".")[1]) if "." in clean else 0
        obj.tol = 0.5 * 10**-decimals
        return obj

    def __reduce__(self):
        """Copies (e.g. deepcopy inside the engine) become plain floats."""
        return (float, (float(self),))


def number(text: str) -> Num:
    """Blueprint numbers use thousands commas and the Unicode minus sign."""
    return Num(text)


def numbers(cell: str) -> list[Num]:
    return [number(x) for x in cell.split("/")]


def section(heading: str) -> str:
    start = BLUEPRINT.index(heading)
    nxt = BLUEPRINT.find("\n### ", start + len(heading))
    return BLUEPRINT[start : nxt if nxt != -1 else None]


def table_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        if not line.startswith("| ") or line.startswith("| Lens") or line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        lens = next(lid for label, lid in LABELS if cells[0].startswith(label))
        rows[lens] = cells[1:]
    return rows


def dry_year() -> dict[str, dict]:
    """§3.1 columns: Q, A, Y, ΣY, E_PJ, E_SE, F, UWF / PWF₃ / EWF / CWF / SWF."""
    out = {}
    for lens, c in table_rows(section("### 3.1 Dry year")).items():
        uwf, pwf3, ewf, cwf, swf = numbers(c[7])
        out[lens] = {
            "Q": numbers(c[0]),
            "A": numbers(c[1]),
            "Y": numbers(c[2]),
            "sumY": number(c[3]),
            "ePJ": number(c[4]),
            "eSE": number(c[5]),
            "F": number(c[6]),
            "welfare": {"UWF": uwf, "PWF3": pwf3, "EWF": ewf, "CWF": cwf, "SWF": swf},
        }
    return out


def normal_year() -> dict[str, dict]:
    """§3.2 columns: Q, A, Y, ΣY, E_PJ, E_SE, F."""
    return {
        lens: {
            "Q": numbers(c[0]),
            "A": numbers(c[1]),
            "Y": numbers(c[2]),
            "sumY": number(c[3]),
            "ePJ": number(c[4]),
            "eSE": number(c[5]),
            "F": number(c[6]),
        }
        for lens, c in table_rows(section("### 3.2 Normal year")).items()
    }


def wet_year() -> dict:
    """§3 prose: 'Wet year (AW = 20): every lens gives Q = … , … Mm³ to the aquifer, A = 1, ΣY = … t, E_PJ = …'."""
    m = re.search(
        r"Wet year \(AW = (\d+)\): every lens gives Q = ([\d. /]+), ([\d.]+) Mm³ to the aquifer, A = 1, "
        r"ΣY = ([\d,]+) t, E\\_PJ = ([\d.]+), E\\_SE = ([\d.]+), F = ([\d.]+), S = (\d+(?:\.\d+)?)",
        BLUEPRINT,
    )
    assert m, "wet-year sentence not found in blueprint §3"
    return {
        "AW": number(m.group(1)),
        "Q": numbers(m.group(2)),
        "surplusToAquifer": number(m.group(3)),
        "sumY": number(m.group(4)),
        "ePJ": number(m.group(5)),
        "eSE": number(m.group(6)),
        "F": number(m.group(7)),
        "S": number(m.group(8)),
    }


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


NUM = r"(−?[\d,]*\d(?:\.\d+)?)"


def grab(pattern: str, text: str) -> list[Num]:
    """Numbers captured by `pattern` (NUM groups) in `text`; fails loudly if the wording changed."""
    m = re.search(pattern.replace("NUM", NUM), text)
    assert m, f"pattern not found in blueprint: {pattern}"
    return [number(g) for g in m.groups()]


def dynamic() -> dict:
    """§3.3 dynamic fixtures and §3.4 cross-checks (full Kelvara scenario, ADR 0007/0008), read from the wording."""
    s33, s34 = section("### 3.3 Dynamic fixtures"), section("### 3.4 Cross-checks")
    p = grab(
        r"W = NUM / NUM / NUM; A = NUM all; ΣY = NUM; F = NUM; S = NUM, r₃ = NUM; B = NUM; cost per Mm³ NUM / NUM / NUM",
        s33,
    )
    dep = grab(r"B = NUM, NUM, NUM, NUM, NUM, NUM after each season; the paddy wells fail in season NUM", s33)
    lost = grab(r"baseflow lost NUM \+ NUM \+ NUM \+ NUM \+ NUM = NUM Mm³", s33)
    coop = grab(r"B stays NUM; spill NUM \(dry\), NUM \(normal\), NUM \(wet\)", s33)
    rf = grab(r"Σ\(1 − βᵢ\)Wᵢ = NUM \+ NUM \+ NUM = NUM Mm³; the share ρ = NUM, NUM, recharges the aquifer and NUM", s33)
    bf = grab(r"B after the season = NUM, NUM, NUM, NUM \| next inflow reduced by NUM, NUM, NUM, NUM Mm³", s33)
    vm = grab(
        r"Dry, utilitarian voted, no pumping \| .*?UWF NUM ranks NUM of 9; PWF₃ NUM ranks NUM of 9; EWF NUM ranks NUM of 9; "
        r"CWF NUM ranks NUM of 9; SWF NUM ranks",
        s33,
    )
    cost = grab(
        r"Pump cost per Mm³ at an observed level B = NUM, NUM, NUM, NUM: A NUM, NUM, NUM, NUM; B NUM, NUM, NUM, NUM; "
        r"C NUM, NUM, NUM, NUM",
        s34,
    )
    marginal = grab(r"A NUM above, NUM below; B NUM above, NUM below; C NUM above, NUM below", s34)
    return {
        "pumping": {"W": p[0:3], "A": p[3], "sumY": p[4], "F": p[5], "S": p[6], "r3": p[7], "B": p[8], "cost": p[9:12]},
        "depletion": {"B": dep[0:6], "paddyWellsFail": dep[6], "baseflowLost": lost[0:5], "baseflowTotal": lost[5]},
        "cooperative": {"B": coop[0], "spill": dict(zip(("dry", "normal", "wet"), coop[1:4], strict=True))},
        "returnFlow": {"parts": rf[0:3], "total": rf[3], "rho": rf[4], "toAquifer": rf[5], "toRiver": rf[6]},
        "baseflow": list(zip(bf[0:4], bf[4:8], strict=True)),
        "equalisandum": grab(r"E\\_SE per claimant NUM; per hectare NUM; per person NUM", s33),
        "verdictMismatch": {"UWF": vm[0], "PWF3": vm[2], "EWF": vm[4], "CWF": vm[6]},
        "capability": grab(r"Capability with κ = 1 in the dry year: E\\_PJ = NUM, per-person E\\_SE = NUM", s34),
        "pumpCost": {"B": cost[0:4], "A": cost[4:8], "Bscheme": cost[8:12], "C": cost[12:16]},
        "marginalPoints": {"A": marginal[0:2], "B": marginal[2:4], "C": marginal[4:6]},
    }


def _row(label_regex: str, text: str) -> list[str]:
    m = re.search(r"^\| " + label_regex + r" \|(.*)$", text, flags=re.M)
    assert m, f"row not found in blueprint: {label_regex}"
    return [c.strip() for c in m.group(1).strip().strip("|").split("|")]


def basin_v1() -> dict:
    """The default basin of §2.1–2.2, in the §3 v1 reduction ('with β = 1 and r₀ = 0'), read from the blueprint."""
    s21, s22 = section("### 2.1 State"), section("### 2.2 Parameters and grounding")
    assert "β = 1, r₀ = 0, no pumping, no actions" in BLUEPRINT
    inflow = grab(r"Wet NUM / Normal NUM / Dry NUM", _row(r"Iₜ", s21)[-1])
    D = numbers(_row(r"Dᵢ,ₜ", s21)[-1])
    K = numbers(_row(r"Kᵢ,ₜ", s21)[-1])
    ky = numbers(_row(r"Yield response Kᵧ", s22)[0])
    N = numbers(_row(r"Livelihoods Nᵢ", s22)[0])
    areas = grab(
        r"NUM ha drip citrus at .*?, NUM ha flooded paddy at .*?, NUM ha sprinkler wheat at", _row(r"Demands Dᵢ", s22)[1]
    )
    B0, Bres, Blow = numbers(_row(r"Aquifer B₀, B\\_res, B\\_low", s22)[0])
    pump = grab(
        r"NUM Mm³; c = NUM \+ NUM\(1 − Bₜ/B₀\) per Mm³, × seat multiplier NUM / NUM / NUM",
        _row(r"Pump cap and cost", s22)[0],
    )
    coupling = grab(r"\(B\\_low − Bₜ\)/B\\_low × NUM Mm³", _row(r"Groundwater–surface coupling", s22)[0])
    reserve = grab(r"^NUM", _row(r"R", s21)[-1])[0]
    price = numbers(_row(r"Crop value pᵢ", s22)[0])  # ADR 0007: harvest value, wheat = 1
    kappa = grab(r"κ default NUM", BLUEPRINT)[0]
    names = ["A", "B", "C"]
    schemes = [
        {
            "id": n,
            "name": n,
            "seat": i + 1,
            "demandMm3": D[i],
            "capacityT": K[i],
            "ky": ky[i],
            "beta": 1.0,
            "people": N[i],
            "kappa": kappa,
            "price": price[i],
            "areaHa": areas[i],
            "pumpCostFactor": 1.0,  # ADR 0008 fields explicit, as the mirror reads them without defaults
            "wellsFailAtOrBelow": None,
        }
        for i, n in enumerate(names)
    ]
    basin = {
        "reserve": reserve,
        "aquifer": {
            "initial": B0,
            "reserve": Bres,
            "lowThreshold": Blow,
            "naturalRecharge": 0.0,
            "seatCostMultipliers": pump[3:6],
            "maxInflowLossMm3": coupling[0],
            "tankResolution": registry()["basin.aquifer.tankResolution"],
            "capacity": None,  # ADR 0006: the §3 fixtures isolate one term each, so the v1 basin is unbounded
            "returnRecharge": 1.0,  # ADR 0007: the v1 reduction sends all return flow (none, β = 1) to the aquifer
            "baseflowLossPerMm3": None,  # ADR 0008: the §2.2 coupling rule
        },  # ADR 0004
        "pump": {"cap": pump[0], "costBase": pump[1], "costSlope": pump[2], "capShare": None},
    }
    plain = json.loads(
        json.dumps({"schemes": schemes, "basin": basin, "inflow": dict(zip(["wet", "normal", "dry"], inflow, strict=True))})
    )
    return plain  # engine inputs as plain floats; expected values keep their printed precision (Num)


def beta_by_method() -> dict[str, Num]:
    """§2.1 βᵢ: 'drip 0.90 / flood 0.60 / sprinkler 0.75'."""
    b = grab(r"drip NUM / flood NUM / sprinkler NUM", _row(r"βᵢ", section("### 2.1 State"))[-1])
    return dict(zip(["drip", "flood", "sprinkler"], b, strict=True))


def natural_recharge() -> Num:
    return number(_row(r"r₀", section("### 2.1 State"))[-1])


def allocable(heading: str) -> Num:
    """'### 3.1 Dry year, AW = 10' → 10."""
    return grab(re.escape(heading) + r", AW = NUM", BLUEPRINT)[0]


# §3 uses two parameter values that differ from the registry defaults; each is read from the blueprint text.
FIXTURE_OVERRIDES = {
    "indicators.welfareGamma": ("PWF₃", 3),  # the subscript of the §3.1 column
    "lenses.prioritarian.gamma": ("Prioritarian (γ = 3 fixture)", 3),
}


def registry() -> dict:
    data = json.loads((ROOT / "packages" / "scenarios" / "parameters.json").read_text(encoding="utf-8"))
    return {p["key"]: p["default"] for p in data["parameters"]}


def fixture_parameters() -> dict:
    """Registry defaults, with the §3 overrides applied (each override's quote must be in the blueprint)."""
    params = registry()
    for key, (quote, value) in FIXTURE_OVERRIDES.items():
        assert quote in BLUEPRINT, f"override quote for {key} not in blueprint"
        params[key] = value
    return params
