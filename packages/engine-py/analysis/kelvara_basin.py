# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The Kelvara basin: Fairflow's default scenario, a hypothetical semi-arid river basin (maintainer decision 2026-10-08).

Every input below is a typical value from the literature, cited as typical, or a labelled teaching convention; nothing is
a measurement of a real place. Derived values (demand, capacity, water productivity, people) are computed here, never
typed. Running this script rewrites the basin and scheme blocks of packages/scenarios/default-basin.json and keeps the
rest of the file (lenses, session, treatments) as it is.

    uv run python analysis/kelvara_basin.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCENARIO = ROOT / "packages" / "scenarios" / "default-basin.json"
HA_MM_TO_MM3 = 1e-5  # unit conversion: 1 ha × 1 mm = 10 m³ = 1e-5 Mm³
T_PER_MM3_TO_KG_PER_M3 = 1e-3  # unit conversion: 1 t per Mm³ = 1e-3 kg per m³
HOUSEHOLD_SIZE = 5  # UN DESA (2022) household-size database: median 4.65 across 26 semi-arid developing countries, rounded
AWU_HOURS, AWU_DAYS = 1800, 225  # Eurostat annual work unit: "1800 hours … (225 working days of eight hours each)"

# ADR 0008: the aquifer's storage–head link and pumping energy. Storage per metre of water-table change = area × specific
# yield (Johnson 1967: alluvium 0.02–0.27; 0.10 for mixed alluvium is a convention), here about 50 km² × 0.10.
STORAGE_PER_M = 5.0  # Mm³ per m (convention)
DEPTH_AT_FULL_M = 7.0  # depth to water when full: 1 m above the shallow wells' suction limit (convention; 6–20 % of
# the world's wells are no more than 5 m deeper than the water table, Jasechko & Perrone 2021)
FLOOR_DEPTH_M = 9.0  # the reserve: pumping stops 2 m below the suction limit (convention)
EXTRA_HEAD_M = 3.0  # well drawdown and delivery head added to the depth (convention)
COST_BASE = 2.0  # points per Mm³ for the most efficient pump set at B₀ (registry actions.pump.costBase; convention)
SUCTION_LIMIT_M = 8.0  # shallow centrifugal pumps fail below about 8 m (Sekhri 2014)

FAO33 = "Doorenbos & Kassam 1979 (FAO-33)"
FAO66 = "Steduto et al. 2012 (FAO-66)"
BROUWER = "Brouwer, Prins & Heibloem 1989 (FAO training manual 4), Annex 1 Table 8"
JAEGERMEYR = "Jägermeyr et al. 2015, HESS 19:3073, Table 5"
FAOSTAT_PRICES = "FAOSTAT producer prices 2019–2023, median of six semi-arid countries, relative to wheat"

# Each scheme: (field, value, source, entered). `entered`: "example" = typical literature value; "assumed" = a stand-in
# where the literature gives none, or a convention.
SCHEMES = [
    {
        "id": "A",
        "name": "Upper Citrus Estate",
        "seat": 1,
        "shape": "circle",
        "glyph": "citrus",
        "crop": "citrus",
        "method": "drip",
        "actions": ["expand"],  # already an orchard on drip: Orchard and Drip would change nothing physical
        "inputs": {
            "areaHa": (625, "a commercial estate; estates of 300–1,500 ha are common (Kan et al. 2024)", "assumed"),
            "depthMm": (1000, f"citrus ET 900–1,200 mm/yr ({FAO33}); gross at drip efficiency", "example"),
            "beta": (0.90, f"drip field application efficiency 90 % ({BROUWER}); 88–90 % ({JAEGERMEYR})", "example"),
            "yieldTHa": (16.0, f"citrus world average ≈ 16 t/ha ({FAO66}, citrus chapter)", "example"),
            "ky": (0.95, f"midpoint of the citrus range 0.8–1.1 ({FAO33})", "example"),
            "price": (1.71, f"fruit (oranges, apples) {FAOSTAT_PRICES}; real ratios vary 1–4× by country", "example"),
            "kappa": (1.0, "capability conversion factor κ = 1 (no conversion handicap assumed)", "assumed"),
        },
        "households": 1,  # one estate owner
        # Junta de Andalucía orange cost study 2022/23: 28.5 worker-days/ha without harvest, harvest 37.6 days at
        # 35,893 kg/ha; harvest scaled to this estate's yield (harvest labour taken proportional to the crop picked)
        "fteHa": (
            (28.5 + 37.6 * 16_000 / 35_893) / AWU_DAYS,
            "hired orchard labour: 28.5 worker-days/ha/yr plus harvest scaled from 37.6 days at 35.9 t/ha to 16 t/ha "
            "(Junta de Andalucía, Costes de producción de la naranja 2022/23), in Eurostat annual work units",
        ),
        "privateGoal": {"kind": "livelihood_share", "threshold": 0.75},
        # submersible pumps; pump-set efficiency about 0.45, the reference (Singh et al. 2023: 40–45 % for good sets)
        "pump": {"pumpCostFactor": 1.0},
    },
    {
        "id": "B",
        "name": "Midstream Paddy Cooperative",
        "seat": 2,
        "shape": "square",
        "glyph": "rice",
        "crop": "rice",
        "method": "flood",
        "actions": ["orchard", "expand"],  # no constant-yield basis for flooded rice on drip (Tuong et al. 2005)
        "inputs": {
            "areaHa": (900, "smallholder paddy; most farms are under 2 ha (Lowder et al. 2016)", "assumed"),
            "depthMm": (
                1000,
                f"irrigated rice input 400 to > 2,000 mm, low end for low-percolation soils ({FAO66})",
                "example",
            ),
            "beta": (0.60, f"surface (basin) application efficiency 60 % ({BROUWER}); 42–62 % ({JAEGERMEYR})", "example"),
            "yieldTHa": (5.0, f"irrigated lowland rice in Asia averages about 5 t/ha ({FAO66})", "example"),
            "ky": (
                1.1,
                "no FAO seasonal Ky for flooded rice; assumed between wheat (1.05–1.15) and maize (1.25)",
                "assumed",
            ),
            "price": (1.99, f"paddy rice {FAOSTAT_PRICES}; real ratios vary 1–4× by country", "example"),
            "kappa": (1.0, "capability conversion factor κ = 1 (no conversion handicap assumed)", "assumed"),
        },
        "householdHa": (1.0, "about 1 ha per household; 84 % of the world's farms are under 2 ha (Lowder et al. 2016)"),
        "fteHa": (
            290 / AWU_HOURS,
            "hired rice labour about 290 h/ha/season (median of 19 Indian states, 2017-18 to 2021-22, DES Cost of "
            "Cultivation; family labour is counted through households), one season a year, in Eurostat annual work units",
        ),
        "privateGoal": {"kind": "adequacy_floor", "threshold": 0.5},
        # shallow centrifugal pumps at about 0.25 efficiency (Singh et al. 2023: 25–30 % average, 21–24 % audited), so
        # 0.45 / 0.25 = 1.8 times the energy per m³; they fail at the suction limit
        "pump": {"pumpCostFactor": 1.8, "wellsFailAtDepthM": SUCTION_LIMIT_M},
    },
    {
        "id": "C",
        "name": "Tail-end Wheat Farms",
        "seat": 3,
        "shape": "triangle",
        "glyph": "wheat",
        "crop": "wheat",
        "method": "sprinkler",
        "actions": ["orchard", "drip", "expand"],
        "inputs": {
            "areaHa": (400, "about 80 family farms of about 5 ha", "assumed"),
            "depthMm": (850, f"wheat ETm 450–650 mm ({FAO33}); gross at sprinkler efficiency", "example"),
            "beta": (0.75, f"sprinkler application efficiency 75 % ({BROUWER}); 69–78 % ({JAEGERMEYR})", "example"),
            "yieldTHa": (5.0, f"irrigated wheat 4–10 t/ha ({FAO66}); good commercial 6–9 t/ha ({FAO33})", "example"),
            "ky": (1.05, f"winter wheat ({FAO66}, Table 1, from {FAO33})", "example"),
            "price": (1.0, "reference crop for the price ratios", "example"),
            "kappa": (1.0, "capability conversion factor κ = 1 (no conversion handicap assumed)", "assumed"),
        },
        "householdHa": (5.0, "about 5 ha per family farm (assumed)"),
        "fteHa": (
            94 / AWU_HOURS,
            "hired wheat labour about 94 h/ha/season (median of 14 Indian states, DES Cost of Cultivation), "
            "in Eurostat annual work units",
        ),
        "privateGoal": {"kind": "adequacy_in_half_seasons", "threshold": 0.8},
        # family-farm pump sets at about 0.30 efficiency (Singh et al. 2023), 0.45 / 0.30 = 1.5; wells fail only at
        # 10 m, below the aquifer's reserve, so never within the game
        "pump": {"pumpCostFactor": 1.5},
    },
]

BASIN = {
    "inflow": {
        "wet": 22,
        "normal": 17,
        "dry": 12,
        "unit": "Mm3/season",
        "dryDrift": 0,
        "source": "Hypothetical Kelvara River. Wet and dry cards read as the 80th and 20th percentiles of seasonal flow, "
        "CV ≈ 0.35, typical of semi-arid steppe rivers (McMahon et al. 1987: annual-flow CV ≈ 0.43 outside Australia "
        "and southern Africa). Deck 1 wet / 3 normal / 2 dry is a teaching convention.",
    },
    "deck": {"wet": 1, "normal": 3, "dry": 2},
    "reserve": {
        "value": 2,
        "mode": "absolute",
        "source": "About 12 % of mean flow: Tennant's 'minimum' (10 % of mean flow; Tennant 1976), below the 20–50 % of "
        "mean annual flow needed to keep a river in fair condition (Smakhtin et al. 2004). Stated openly in the game.",
    },
    "aquifer": {
        "initial": 20,
        "capacity": 20,
        "reserve": None,  # derived in main() from the depths (ADR 0008)
        "lowThreshold": None,
        "naturalRecharge": 1.0,
        "surplusRecharge": True,
        "returnFlows": True,
        # convention 0.6 inside the 0.4–0.75 supported by Karimi et al. 2013 (Indus: 0.43 of field returns, 0.71 with
        # canal seepage) and India's GEC-2015 recharge norms (about 0.5–0.75 at water tables shallower than 25 m)
        "returnRecharge": 0.6,
        # ADR 0008: baseflow lost per Mm³ below full, κ = 0.1 (convention; pumping captures streamflow, Konikow &
        # Leake 2014; Barlow & Leake 2012). maxInflowLossMm3 is kept for the schema and unused when κ is given.
        "gwSwCoupling": {"enabled": True, "maxInflowLossMm3": 1.0, "lossPerMm3BelowFull": 0.1},
        "seatCostMultipliers": [1.0, 1.0, 1.0],  # ADR 0008: replaced by each scheme's pumpCostFactor
        "source": "Hypothetical shared alluvial aquifer of about 50 km² with specific yield about 0.10 (Johnson 1967), so "
        "5 Mm³ of storage per metre of water-table change (ADR 0008). Full (20 Mm³) at 7 m depth; the low threshold, "
        "15 Mm³, is 8 m, the suction limit of shallow pumps (Sekhri 2014); the reserve, 10 Mm³, is 9 m. Natural recharge "
        "1 Mm³ per year ≈ 20 mm/yr, within the semi-arid range 0.2–35 mm/yr (Scanlon et al. 2006); a share of return "
        "flow recharges it too. One round is one irrigation year. Storage, depths and coupling are conventions.",
    },
    "gameLength": {"min": 5, "max": 6},
}


def scheme_block(s: dict) -> dict:
    v = {k: x[0] for k, x in s["inputs"].items()}
    demand = v["areaHa"] * v["depthMm"] * HA_MM_TO_MM3
    capacity = v["areaHa"] * v["yieldTHa"]
    households = s.get("households", v["areaHa"] / s.get("householdHa", (1.0,))[0])
    fte = v["areaHa"] * s["fteHa"][0]
    people = round((households + fte) * HOUSEHOLD_SIZE)
    fields = {k: {"source": x[1], "entered": x[2], "outOfRange": False} for k, x in s["inputs"].items()}
    house_note = f"{s['householdHa'][1]}; " if "householdHa" in s else "one owner household; "
    fields["people"] = {
        "source": f"(households + FTE hired workers) × {HOUSEHOLD_SIZE}: {house_note}{s['fteHa'][1]}. "
        f"= ({households:g} + {fte:.1f}) × {HOUSEHOLD_SIZE}, a typical estimate",
        "entered": "derived",
        "outOfRange": False,
    }
    return {
        "id": s["id"],
        "name": s["name"],
        "seat": s["seat"],
        "shape": s["shape"],
        "glyph": s["glyph"],
        "crop": s["crop"],
        "method": s["method"],
        "actions": s["actions"],
        **{k: v[k] for k in ("areaHa", "depthMm", "beta", "yieldTHa", "ky")},
        "people": people,
        "peopleUnit": "people",
        "kappa": v["kappa"],
        "price": v["price"],
        "derived": {
            "demandMm3": round(demand, 6),
            "capacityT": round(capacity, 6),
            "wpKgM3": round(capacity / demand * T_PER_MM3_TO_KG_PER_M3, 2),  # printed to 2 decimals, checked at load
        },
        "privateGoal": s["privateGoal"],
        "fields": fields,
    }


def main() -> None:
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    # REUSE-IgnoreStart (this text is written into the generated CC-BY-4.0 scenario)
    scenario["$comment"] = (
        "SPDX-License-Identifier: CC-BY-4.0 · The Kelvara basin, a hypothetical semi-arid river basin. Generated by "
        "packages/engine-py/analysis/kelvara_basin.py: every value is a typical literature value or a labelled "
        "convention, and derived values are computed there. Not a model of any real place."
    )
    # REUSE-IgnoreEnd
    scenario["name"] = "Kelvara basin (hypothetical)"
    citrus = SCHEMES[0]["inputs"]  # the estate's crop is the basin's orchard crop (ADR 0007, Orchard)
    scenario["basin"] = {
        **BASIN,
        "orchardCrop": {
            "crop": SCHEMES[0]["crop"],
            **{k: citrus[k][0] for k in ("depthMm", "beta", "yieldTHa", "ky", "price")},
            "source": "Orchard switches a scheme to the basin's orchard crop, the citrus of the Upper Citrus Estate, at "
            "the scheme's own area and irrigation method; values and sources as for scheme A",
        },
    }
    scenario["schemes"] = [scheme_block(s) for s in SCHEMES]
    b0 = BASIN["aquifer"]["initial"]
    aq = scenario["basin"]["aquifer"]
    aq["lowThreshold"] = b0 - STORAGE_PER_M * (SUCTION_LIMIT_M - DEPTH_AT_FULL_M)
    aq["reserve"] = b0 - STORAGE_PER_M * (FLOOR_DEPTH_M - DEPTH_AT_FULL_M)
    for block, s in zip(scenario["schemes"], SCHEMES, strict=True):
        pump = s["pump"]
        block["pumpCostFactor"] = pump["pumpCostFactor"]
        if "wellsFailAtDepthM" in pump:  # depth → stock: B = B₀ − storage per metre × (depth − depth at full)
            block["wellsFailAtOrBelow"] = b0 - STORAGE_PER_M * (pump["wellsFailAtDepthM"] - DEPTH_AT_FULL_M)
    # pumping energy is linear in the head (E = ρgH/η): c(B) = c₀ (1 + (B₀ − B) / (storage per m × head at B₀))
    slope = COST_BASE * b0 / (STORAGE_PER_M * (DEPTH_AT_FULL_M + EXTRA_HEAD_M))
    scenario["actions"] = {
        "pump": {
            "capShare": 0.5,
            "costBase": COST_BASE,
            "costSlope": round(slope, 6),
            "source": "ADR 0008. capShare 0.5 inside the 0.38 (world) to 0.57 (South Asia) share of irrigation from "
            "groundwater (Siebert et al. 2010); cost is lift energy, linear in the head, costSlope = costBase × B₀ / "
            "(storage per metre × head at B₀) with head 7 m + 3 m; costBase is a convention in points.",
        }
    }
    SCENARIO.write_text(json.dumps(scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for s in scenario["schemes"]:
        print(s["id"], s["name"], s["derived"], "people", s["people"])


if __name__ == "__main__":
    main()
