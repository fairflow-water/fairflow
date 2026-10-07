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
    """§3.3 dynamic fixtures and §3.4 cross-checks, read from the blueprint wording."""
    s33, s34 = section("### 3.3 Dynamic fixtures"), section("### 3.4 Cross-checks")
    W = grab(
        r"W = NUM / NUM / NUM; A ≥ 1 all; ΣY = NUM; F = NUM; S = NUM, r₃ = NUM; B = NUM; cost NUM × NUM = NUM each", s33
    )
    dep = grab(r"B = NUM, NUM, NUM; season 3 rations NUM requests to NUM \(NUM each\)", s33)
    costs = grab(r"pump cost of NUM at B₀, NUM at NUM, NUM at NUM and NUM at NUM", s34)
    seats = grab(r"seat multipliers price out B \(NUM\) and C \(NUM\)", s34)
    return {
        "pumping": {"pumps": W[9], "W": W[0:3], "sumY": W[3], "F": W[4], "S": W[5], "r3": W[6], "B": W[7], "spend": W[10]},
        "depletion": {"B": dep[0:3], "requests": dep[3], "rationedTotal": dep[4], "each": dep[5]},
        "returnFlow": grab(r"Σ\(1 − βᵢ\)Wᵢ = NUM \+ NUM \+ NUM = NUM Mm³ plus r₀", s33),
        "coupling": grab(r"\| GW–SW coupling \| B falls to NUM \| next inflow reduced by NUM Mm³", s33),
        "equalisandum": grab(r"E\\_SE per claimant NUM; per hectare NUM \(= E\\_PJ\); per person NUM", s33),
        "verdictMismatch": grab(
            r"UWF NUM is the highest UWF of any lens in this season \(column-wise comparison\); PWF₃ NUM, SWF NUM", s33
        ),
        "capabilityPerPerson": grab(r"per-person E\\_SE is highest \(NUM\)", s34)[0],
        "pumpCost": {"atB0": costs[0], "pairs": [(costs[i + 1], costs[i]) for i in (1, 3, 5)]},
        "seatCostAt8": {"B": seats[0], "C": seats[1]},
    }


def _row(label_regex: str, text: str) -> list[str]:
    m = re.search(r"^\| " + label_regex + r" \|(.*)$", text, flags=re.M)
    assert m, f"row not found in blueprint: {label_regex}"
    return [c.strip() for c in m.group(1).strip().strip("|").split("|")]


def basin_v1() -> dict:
    """The default basin of §2.1–2.2, in the §3 v1 reduction ('with β = 1 and r₀ = 0'), read from the blueprint."""
    s21, s22 = section("### 2.1 State"), section("### 2.2 Parameters and grounding")
    assert "with β = 1 and r₀ = 0" in BLUEPRINT
    inflow = grab(r"Wet NUM / Normal NUM / Dry NUM", _row(r"Iₜ", s21)[-1])
    D = numbers(_row(r"Dᵢ,ₜ", s21)[-1])
    K = numbers(_row(r"Kᵢ,ₜ", s21)[-1])
    ky = numbers(_row(r"Yield response Kᵧ", s22)[0])
    N = numbers(_row(r"Livelihoods Nᵢ", s22)[0])
    areas = grab(
        r"NUM ha drip orchard at .*?, NUM ha flooded paddy .*?, NUM ha sprinkler cereals", _row(r"Demands Dᵢ", s22)[1]
    )
    B0, Bres, Blow = numbers(_row(r"Aquifer B₀, B\\_res, B\\_low", s22)[0])
    pump = grab(
        r"NUM Mm³; c = NUM \+ NUM\(1 − Bₜ/B₀\) per Mm³, × seat multiplier NUM / NUM / NUM",
        _row(r"Pump cap and cost", s22)[0],
    )
    coupling = grab(r"\(B\\_low − Bₜ\)/B\\_low × NUM Mm³", _row(r"Groundwater–surface coupling", s22)[0])
    reserve = grab(r"^NUM", _row(r"R", s21)[-1])[0]
    price = grab(r"at p = NUM", BLUEPRINT)[0]
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
            "price": price,
            "areaHa": areas[i],
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
        },  # ADR 0004
        "pump": {"cap": pump[0], "costBase": pump[1], "costSlope": pump[2]},
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
