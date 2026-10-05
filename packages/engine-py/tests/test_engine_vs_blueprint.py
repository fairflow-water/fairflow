# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
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


def test_pumping():
    want = bp.dynamic()["pumping"]
    r = season("proportional", "normal", pumps=[want["pumps"]] * 3)
    for i in range(3):
        near(r["W"][i], want["W"][i], f"W[{i}]")
        assert r["A"][i] >= 1
    near(sum(r["Y"]), want["sumY"], "ΣY")
    near(r["F"]["consumed"], want["F"], "F")
    near(r["S"], want["S"], "S")
    near(r["triangle"]["r3"], want["r3"], "r3")
    near(r["stockNext"], want["B"], "B")
    for c, p in zip(r["pumpCost"], r["P"], strict=True):
        near(c * p, want["spend"], "pump spend")


def test_depletion():
    want = bp.dynamic()["depletion"]
    stock, loss, stocks = BASIN.aquifer.initial, 0.0, []
    for card in ("dry", "dry", "normal"):
        r = season("proportional", card, pumps=[2, 2, 2], stock=stock, inflow=INFLOW[card] - loss)
        stock, loss = r["stockNext"], r["inflowLossNext"]
        stocks.append(stock)
    for got, w in zip(stocks, want["B"], strict=True):
        near(got, w, "B path")
    near(r["pumpsTotal"], want["rationedTotal"], "rationed total")
    for p in r["P"]:
        near(p, want["each"], "rationed each")


def test_pump_cost_and_seat_multipliers():
    d = bp.dynamic()
    near(pump_cost_per_mm3(BASIN, BASIN.aquifer.initial, 1), d["pumpCost"]["atB0"], "cost at B0")
    for B, cost in d["pumpCost"]["pairs"]:
        near(pump_cost_per_mm3(BASIN, B, 1), cost, f"cost at B={B}")
    near(pump_cost_per_mm3(BASIN, 8, 2), d["seatCostAt8"]["B"], "seat B at 8")
    near(pump_cost_per_mm3(BASIN, 8, 3), d["seatCostAt8"]["C"], "seat C at 8")


def test_return_flow_beta_set():
    *parts, total = bp.dynamic()["returnFlow"]
    beta = bp.beta_by_method()
    schemes = [replace(s, beta=beta[m]) for s, m in zip(SCHEMES, ["drip", "flood", "sprinkler"], strict=True)]
    basin = replace(BASIN, aquifer=replace(BASIN.aquifer, naturalRecharge=bp.natural_recharge()))
    r = season("proportional", "normal", schemes=schemes, basin=basin)
    for s, w, part in zip(schemes, r["W"], parts, strict=True):
        near((1 - s.beta) * w, part, "return part")
    near(r["returnFlow"], total, "return total")
    assert r["stockNext"] == pytest.approx(BASIN.aquifer.initial + r["returnFlow"] + bp.natural_recharge())


def test_coupling():
    B, cut = bp.dynamic()["coupling"]
    near(inflow_loss_next(BASIN, B), cut, "inflow cut")


def test_equalisandum():
    claimant, hectare, person = bp.dynamic()["equalisandum"]
    r = season("proportional", "dry")
    near(r["eSE"]["claimant"], claimant, "per claimant")
    near(r["eSE"]["hectare"], hectare, "per hectare")
    near(r["eSE"]["person"], person, "per person")


def test_capability_per_person_is_highest():
    want = bp.dynamic()["capabilityPerPerson"]
    cap = season("capability", "dry")
    assert cap["ePJ"] < 0
    near(cap["eSE"]["person"], want, "capability per-person E_SE")
    assert all(season(lens, "dry")["eSE"]["person"] <= cap["eSE"]["person"] for lens in LENSES)


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
    uwf, pwf3, swf = bp.dynamic()["verdictMismatch"]
    u = season("utilitarian", "dry")
    near(u["welfare"]["UWF"], uwf, "UWF")
    near(u["welfare"]["PWF"], pwf3, "PWF3")
    near(u["welfare"]["SWF"], swf, "SWF")
    assert all(season(lens, "dry")["welfare"]["UWF"] <= u["welfare"]["UWF"] for lens in LENSES)


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
