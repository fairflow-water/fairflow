# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The engine against blueprint §3: every expected value, and its tolerance (half a unit of the last printed digit),
is read from docs/blueprint.md. Nothing here is typed by hand."""

from dataclasses import replace

import blueprint as bp
import pytest

from fairflow_engine import Basin, LensParams, Scheme, Scoring, inflow_loss_next, pump_cost_per_mm3, resolve_season, verdict

BASE = bp.basin_v1()
SCHEMES = [Scheme.from_dict(s) for s in BASE["schemes"]]
BASIN = Basin.from_dict(BASE["basin"])
INFLOW = BASE["inflow"]
PARAMS = bp.fixture_parameters()
SCORING = Scoring(
    r3Ramp=PARAMS["indicators.r3Ramp"],
    welfareGamma=PARAMS["indicators.welfareGamma"],
    survivalFloor=PARAMS["indicators.survivalFloor"],
    welfareSupplyFloor=PARAMS["indicators.welfareSupplyFloor"],
    sustainabilityBands=tuple(PARAMS["indicators.sustainabilityBands"]),
)
LENSES = [
    "utilitarian",
    "weighted_utilitarian",
    "egalitarian",
    "proportional",
    "capability",
    "sufficientarian",
    "prioritarian",
    "equal_sacrifice",
    "talmud",
]


def lens_params(lens: str) -> LensParams:
    prefix = f"lenses.{lens}."
    return LensParams(**{k[len(prefix) :]: v for k, v in PARAMS.items() if k.startswith(prefix)})


def season(lens="proportional", card="normal", pumps=(0, 0, 0), stock=None, schemes=SCHEMES, basin=BASIN, inflow=None):
    return resolve_season(
        schemes,
        basin,
        INFLOW[card] if inflow is None else inflow,
        basin.aquifer.initial if stock is None else stock,
        lens,
        lens_params(lens),
        list(pumps),
        SCORING,
    )


def near(got: float, want: bp.Num, what: str):
    assert abs(got - want) <= want.tol + 1e-9, f"{what}: engine {got} vs blueprint {float(want)} (±{want.tol})"


def test_fixture_file_basin_equals_blueprint():
    """The TypeScript fixtures carry a copy of the basin; it must equal the blueprint's."""
    v1 = bp.fixture("default-basin-v1.json")
    assert v1["schemes"] == [{**s, "name": f["name"]} for s, f in zip(BASE["schemes"], v1["schemes"], strict=True)]
    for k in ("reserve",):
        assert v1["basin"][k] == BASE["basin"][k]
    assert v1["basin"]["aquifer"] == BASE["basin"]["aquifer"]
    assert v1["basin"]["pump"] == BASE["basin"]["pump"]
    assert v1["basin"]["inflow"] == INFLOW


def test_allocable_water_per_card():
    assert season(card="dry")["allocable"] == bp.allocable("### 3.1 Dry year")
    assert season(card="normal")["allocable"] == bp.allocable("### 3.2 Normal year")


@pytest.mark.parametrize("card,table", [("dry", bp.dry_year), ("normal", bp.normal_year)])
def test_reference_vectors(card, table):
    assert "S = 1.00 and r₃ = 1 in every row" in bp.BLUEPRINT
    for lens, want in table().items():
        r = season(lens, card)
        for i in range(3):
            near(r["allocation"]["Q"][i], want["Q"][i], f"{card} {lens} Q[{i}]")
            near(r["A"][i], want["A"][i], f"{card} {lens} A[{i}]")
            near(r["Y"][i], want["Y"][i], f"{card} {lens} Y[{i}]")
        near(sum(r["Y"]), want["sumY"], f"{card} {lens} ΣY")
        near(r["ePJ"], want["ePJ"], f"{card} {lens} E_PJ")
        near(r["eSE"]["claimant"], want["eSE"], f"{card} {lens} E_SE")
        near(r["F"]["consumed"], want["F"], f"{card} {lens} F")
        assert r["S"] == pytest.approx(1.0) and r["triangle"]["r3"] == 1
        for k, v in want.get("welfare", {}).items():
            near(r["welfare"]["PWF" if k == "PWF3" else k], v, f"{card} {lens} {k}")


@pytest.mark.parametrize("lens", LENSES)
def test_wet_year(lens):
    want, r = bp.wet_year(), season(lens, "wet")
    for i in range(3):
        near(r["allocation"]["Q"][i], want["Q"][i], f"wet {lens} Q[{i}]")
    near(r["allocation"]["surplusToAquifer"], want["surplusToAquifer"], "wet surplus")
    near(sum(r["Y"]), want["sumY"], "wet ΣY")
    for k in ("ePJ", "F", "S"):
        near(r[k] if k != "F" else r["F"]["consumed"], want[k], f"wet {k}")
    near(r["eSE"]["claimant"], want["eSE"], "wet E_SE")


# ---- §3.3 and §3.4 in the full Kelvara scenario (ADR 0007, ADR 0008), loaded as a game loads it -----------------------
def kelvara():
    import json

    from fairflow_engine.scenario import load_scenario

    scenario = json.loads((bp.ROOT / "packages" / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))
    return load_scenario(scenario, bp.registry()).setup


FULL = kelvara()


def full_season(card, pumps, stock, loss=0.0, lens="proportional"):
    params = dict(FULL.lenses)[lens]
    return resolve_season(FULL.schemes, FULL.basin, FULL.inflow[card] - loss, stock, lens, params, pumps, FULL.scoring)


def caps(stock):
    from fairflow_engine.aquifer import pump_cap

    return [pump_cap(FULL.basin, stock, s) for s in FULL.schemes]


def test_pumping():
    want = bp.dynamic()["pumping"]
    b0 = FULL.basin.aquifer.initial
    r = full_season("normal", caps(b0), b0)
    for i in range(3):
        near(r["W"][i], want["W"][i], f"W[{i}]")
        near(r["A"][i], want["A"], f"A[{i}]")
        near(r["pumpCost"][i], want["cost"][i], f"cost[{i}]")
    near(sum(r["Y"]), want["sumY"], "ΣY")
    near(r["F"]["consumed"], want["F"], "F")
    near(r["S"], want["S"], "S")
    near(r["triangle"]["r3"], want["r3"], "r3")
    near(r["stockNext"], want["B"], "B")


def test_selfish_depletion_dries_the_paddy_wells_and_takes_baseflow():
    """§3.3 'Selfish depletion' (ADR 0008): each scheme pumps its capacity every season; caps follow the observed level."""
    want = bp.dynamic()["depletion"]
    stock, loss, path, lost, failed = FULL.basin.aquifer.initial, 0.0, [], [], None
    for n, card in enumerate(("dry", "dry", "normal", "normal", "wet", "dry"), start=1):
        c = caps(stock)
        if c[1] == 0 and failed is None:
            failed = n
        r = full_season(card, c, stock, loss)
        stock, loss = r["stockNext"], r["inflowLossNext"]
        path.append(stock)
        lost.append(loss)
    for got, w in zip(path, want["B"], strict=True):
        near(got, w, "B path")
    assert failed == int(want["paddyWellsFail"])
    for got, w in zip(lost, want["baseflowLost"], strict=False):  # the loss after each of the first five seasons
        near(got, w, "baseflow lost")
    near(sum(lost[:5]), want["baseflowTotal"], "baseflow total")


def test_cooperation_keeps_the_aquifer_full_and_spilling():
    want = bp.dynamic()["cooperative"]
    b0 = FULL.basin.aquifer.initial
    for card in ("dry", "normal", "wet"):
        r = full_season(card, [0, 0, 0], b0)
        near(r["stockNext"], want["B"], f"{card} B")
        near(r["spill"], want["spill"][card], f"{card} spill")


def test_return_flow_splits_between_aquifer_and_river():
    want = bp.dynamic()["returnFlow"]
    r = full_season("normal", [0, 0, 0], FULL.basin.aquifer.initial)
    parts = [(1 - s.beta) * w for s, w in zip(FULL.schemes, r["W"], strict=True)]
    for got, w in zip(parts, want["parts"], strict=True):
        near(got, w, "return part")
    near(sum(parts), want["total"], "return total")
    assert FULL.basin.aquifer.returnRecharge == pytest.approx(float(want["rho"]))
    near(r["returnFlow"], want["toAquifer"], "to the aquifer")
    near(sum(parts) - r["returnFlow"], want["toRiver"], "to the river")


def test_baseflow_loss():
    for B, cut in bp.dynamic()["baseflow"]:
        near(inflow_loss_next(FULL.basin, float(B)), cut, f"inflow cut at B={B}")


def test_pump_cost_by_scheme_and_level():
    d = bp.dynamic()["pumpCost"]
    for k, B in enumerate(d["B"]):
        for scheme, key in zip(FULL.schemes, ("A", "Bscheme", "C"), strict=True):
            near(pump_cost_per_mm3(FULL.basin, float(B), scheme.seat, scheme.pumpCostFactor), d[key][k], f"{key} at {B}")


def test_marginal_value_points():
    from fairflow_engine.production import value_of

    floor = FULL.scoring.survivalFloor
    for s, key in zip(FULL.schemes, ("A", "B", "C"), strict=True):
        above_want, below_want = bp.dynamic()["marginalPoints"][key]
        kink, d = floor * s.demandMm3, s.demandMm3
        near((value_of(s, d, floor) - value_of(s, kink, floor)) / (d - kink) / 100, above_want, f"{key} above")
        near(value_of(s, kink, floor) / kink / 100, below_want, f"{key} below")


def test_equalisandum():
    claimant, hectare, person = bp.dynamic()["equalisandum"]
    r = season("proportional", "dry")
    near(r["eSE"]["claimant"], claimant, "per claimant")
    near(r["eSE"]["hectare"], hectare, "per hectare")
    near(r["eSE"]["person"], person, "per person")


def test_capability_per_person_is_highest():
    epj, per_person = bp.dynamic()["capability"]
    cap = season("capability", "dry")
    near(cap["ePJ"], epj, "capability E_PJ")
    near(cap["eSE"]["person"], per_person, "capability per-person E_SE")
    assert all(season(lens, "dry")["eSE"]["person"] <= cap["eSE"]["person"] + 1e-9 for lens in LENSES)


def test_verdict_match():
    r = season("proportional", "dry")
    v = verdict(
        SCHEMES,
        r["allocable"],
        r["W"],
        "proportional",
        r["pumpsTotal"],
        [(lens, lens_params(lens)) for lens in LENSES],
        SCORING.survivalFloor,
    )
    assert (v["satisfied"], v["pumpingGap"]) == ("proportional", 0)
    assert all(season(lens, "dry")["welfare"]["EWF"] <= r["welfare"]["EWF"] for lens in LENSES)


def test_verdict_mismatch_utilitarian():
    """§3.3: with no pumping the verdict matches the vote; the welfare columns do not favour the utilitarian lens."""
    want = bp.dynamic()["verdictMismatch"]
    u = season("utilitarian", "dry")
    near(u["welfare"]["UWF"], want["UWF"], "UWF")
    near(u["welfare"]["PWF"], want["PWF3"], "PWF3")
    near(u["welfare"]["EWF"], want["EWF"], "EWF")
    near(u["welfare"]["CWF"], want["CWF"], "CWF")
    egal = season("egalitarian", "dry")["welfare"]["UWF"]
    assert all(season(lens, "dry")["welfare"]["UWF"] <= egal + 1e-9 for lens in LENSES)


def test_prioritarian_limits():
    tol = bp.grab(r"within NUM of strict egalitarian and proportional", bp.BLUEPRINT)[0]
    g_low, g_high = bp.grab(r"γ = NUM and NUM \| within", bp.BLUEPRINT)
    egal, prop = season("egalitarian", "dry"), season("proportional", "dry")
    for g, ref in ((g_low, egal), (g_high, prop)):
        r = resolve_season(
            SCHEMES,
            BASIN,
            INFLOW["dry"],
            BASIN.aquifer.initial,
            "prioritarian",
            replace(lens_params("prioritarian"), gamma=float(g)),
            [0, 0, 0],
            SCORING,
        )
        for q, q_ref in zip(r["allocation"]["Q"], ref["allocation"]["Q"], strict=True):
            assert abs(q - q_ref) <= tol
