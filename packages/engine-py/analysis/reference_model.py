# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Independent reference implementation of the Fairflow model (blueprint §2).

Purpose
-------
Regenerates the blueprint's §3 worked examples ("reference vectors and
fixtures") for the shipped scenario. It is written from the specification
only -- blueprint §2-§4 and §9.2, ADR 0003, ADR 0006, ADR 0007 and ADR 0008
(where the blueprint text and ADRs 0007/0008 differ, the ADRs win) -- and it
neither reads nor imports the engine (`packages/engine-py/src`,
`packages/engine/src`), its tests or the balance harness. The engine's tests
compare the engine against §3, so the two must stay independent
implementations.

Scheme, basin and pump values are read at run time from
`packages/scenarios/default-basin.json` (including `actions.pump`,
`basin.orchardCrop`, `basin.aquifer.returnRecharge`,
`gwSwCoupling.lossPerMm3BelowFull`, scheme `pumpCostFactor`,
`wellsFailAtOrBelow` and `actions`); model parameters (survival floor, welfare
supply floor, γ, r₃ ramp, action costs and factors, tank resolution, ...) from
the registry `packages/scenarios/parameters.json`. Only equations and
constants that the specification states and that neither file carries are
written here, each with its section.

Everything is computed in double precision; values are rounded only when
printed (two decimals, integers for tonnes and value), as §3 does.

Run:  cd packages/engine-py && uv run python analysis/reference_model.py

Ambiguities (and the reading chosen)
------------------------------------
A1  Utilitarian rule. §2.3 says "greedy by marginal value over the
    piecewise-linear production function". With Kᵧ > 1 the function is convex
    above the survival kink (the marginal value rises), so greedy is not
    optimal. Reading: maximise Σ pᵢYᵢ exactly (vertex enumeration, see
    `max_value`). Ties in value are broken leximin-in-adequacy among the
    optimal vertices; a tie is reported if it occurs.
A2  Weighted utilitarian. §2.3 gives Cᵢ = Kᵢ/Dᵢ (tonnes); ADR 0007 §3 says the
    utilitarian lenses (plural) add value. Reading: Cᵢ = pᵢKᵢ/Dᵢ.
A3  Sufficientarian. Floors 0.5·Dᵢ (registry `lenses.sufficientarian.floor`);
    if Σ floors ≥ AW they are cut by the registry's `floorScaling`
    ("whatever works" = proportional, ADR 0003); otherwise the remainder goes
    by `secondary` = max value, solved exactly with the floors as lower bounds.
A4  Prioritarian γ. §3 tables use the "γ = 3 fixture"; the registry default
    for play is γ = 2. The §3 tables use γ = 3 with an extra γ = 2 row; the
    verdict (a play-time quantity) uses γ = 2; goal attainability reports
    both. Weights w = 1 (registry).
A5  Adequacy in indicators. §2.4 defines Aᵢ = Wᵢ/Dᵢ (uncapped). E_PJ uses this
    uncapped A (pumping beyond need lowers E_PJ only through dispersion); the
    welfare functions use sᵢ = min(Aᵢ, 1) floored at 0.01 (§2.7). E_PJ and
    E_SE are printed unclipped; r₁ = clip(E_PJ, 0, 1) before the composite.
A6  Surplus. §2.3 writes B ← B + (AW − ΣQ); §2.6 writes max(0, AW − ΣDᵢ). They
    agree whenever a lens hands out min(AW, ΣD), which every lens here does
    (asserted). Reading: AW − ΣQ.
A7  Rationing (§2.6, R11, ADR 0008). Requests (each already capped at the
    scheme's capacity) are cut pro rata to the TRUE stock above the reserve,
    Bₜ − B_res, before the season's recharge and return flows arrive; so the
    max(B_res, ·) of §2.6 never binds (asserted). Capacity, well failure, the
    pump cost and the baseflow loss use the OBSERVED stock (ADR 0004: the
    true stock floored to `basin.aquifer.tankResolution`, 1 Mm³, with a 1e-9
    tolerance against float noise). The task statement names the observed
    stock for capacity, cost and baseflow but not for rationing; the true
    stock is the physical limit, so rationing uses it.
A8  Pump capacity (ADR 0008 §3): capShare × Dᵢ with `actions.pump.capShare`
    from the scenario (it overrides the registry default; equal here), so it
    grows with Expand and changes with Orchard and Drip (both change D). It is
    0 for a scheme with `wellsFailAtOrBelow` once the observed stock is at or
    below that level. A selfish request is "pump the full capacity", even when
    W then exceeds D (A > 1).
A9  Pump cost (ADR 0006 §1, ADR 0008 §4): c = pumpCostFactorᵢ × (costBase +
    costSlope·max(0, 1 − B_obs/B₀)), × the seat multiplier once B_obs < B_low
    (§2.2; the scenario multipliers are all 1). costBase and costSlope come
    from the scenario's `actions.pump`, which overrides the registry's v1
    values (2, 6).
A10 Baseflow (ADR 0008 §6): next season's inflow falls by
    κ·max(0, B₀ − B_obs,ₜ₊₁), κ = `gwSwCoupling.lossPerMm3BelowFull`. The
    scenario also carries `maxInflowLossMm3` = 1; ADR 0008 does not say it
    caps the new rule. With B ≥ B_res = 10 the loss is at most κ·10 = 1, so
    the question is moot here; no cap is applied.
A11 One round = one irrigation year (ADR 0008 §1): r₀ is added once per round.
A12 v1 reduction (§2.6, §3): β = 1, r₀ = 0, no pumping, no actions, no
    aquifer capacity (ADR 0006 §3). Under β = 1 the return flow is 0, so ρ
    plays no part. Only single-season static tables are computed in the v1
    reduction; every dynamic fixture uses the full scenario. Prices are kept
    (ADR 0007 makes them part of the model).
A13 Drip (ADR 0007 §6): C′ = c_drip·βᵢ·Dᵢ, D′ = C′/β_drip, β′ = β_drip; K and
    area unchanged; c_drip = registry `actions.drip.consumptionFactor`, β_drip
    = `actions.drip.betaAfter`.
A14 Orchard (ADR 0007 §8, §4.3): from t+1 the scheme takes the basin's
    orchard crop and keeps the tree's consumption: D = area × depthMm ×
    orchardCrop.beta / βᵢ (1 ha × 1 mm = 10 m³), K = area × yieldTHa, Kᵧ and p
    of `basin.orchardCrop`; βᵢ (the scheme's method) unchanged.
A15 Goal attainability (§4.4 R15, ADR 0008 §7). A: cumulative ΔL ≥ threshold
    × full-demand potential, potential = Σₜ pK/100; B: adequacy never below
    the threshold (1e-9 tolerance, so the sufficientarian A = 0.5 meets it);
    C: adequacy ≥ threshold in at least half the seasons. All decks are the
    distinct orders of 1W/3N/2D (60, all equally likely under a uniform
    shuffle); T = 5 plays the first five cards, so its 60 distinct five-card
    sequences are also equally likely. Without pumping S ≤ 1, so the aquifer
    never falls below B₀ and order cannot matter; the enumeration confirms it.
A16 Verdict (§2.7): the lens(es) whose ideal allocation is nearest the
    realised one by Σ|Aᵢ − Aᵢ*|; on a tie the voted lens is named (task
    rule). Computed over all nine lenses and over the scenario's enabled
    lenses; welfare-column ranks are over the nine §3.1 rows.
A17 Welfare (§2.7): EWF = 1 − Gini without the n/(n−1) correction; PWF_γ is
    printed as the raw sum (the §3 "engine fixture" form). SWF: sᵢ < mᵢ uses a
    1e-9 tolerance so an adequacy of exactly 0.5 is not below the floor.
A18 §2 says stored numbers are rounded to 1e-6 at event boundaries; this
    model carries full double precision between seasons. Printing rounds
    half away from zero on the shortest decimal form (3.125 → 3.13,
    4,362.5 → 4,363), not Python's round-half-even.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCENARIO_PATH = ROOT / "packages" / "scenarios" / "default-basin.json"
REGISTRY_PATH = ROOT / "packages" / "scenarios" / "parameters.json"

EPS = 1e-9
MM_HA_TO_MM3 = 10.0 / 1e6  # 1 ha × 1 mm = 10 m³

# ---------------------------------------------------------------------------
# Inputs: scenario (basin, schemes, pump) and registry (parameters)
# ---------------------------------------------------------------------------


def load_registry() -> dict:
    reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {p["key"]: p["default"] for p in reg["parameters"]}


REG = load_registry()
SURVIVAL = float(REG["indicators.survivalFloor"])  # §2.7 mᵢ = 0.5
SUPPLY_FLOOR = float(REG["indicators.welfareSupplyFloor"])  # §2.7 sᵢ floored at 0.01
WELFARE_GAMMA = float(REG["indicators.welfareGamma"])  # §2.7 PWF₃ (ADR 0003)
R3_RAMP = float(REG["indicators.r3Ramp"])  # §2.5 (S − 1)/0.6
PRIO_GAMMA_DEFAULT = float(REG["lenses.prioritarian.gamma"])  # §2.3 default γ = 2
PRIO_GAMMA_FIXTURE = 3.0  # §3: "Prioritarian (γ = 3 fixture)"
SUFF_FLOOR = float(REG["lenses.sufficientarian.floor"])
SUFF_SCALING = REG["lenses.sufficientarian.floorScaling"]
SUFF_SECONDARY = REG["lenses.sufficientarian.secondary"]
ORCHARD_COST = float(REG["actions.orchard.cost"])
DRIP_COST = float(REG["actions.drip.cost"])
DRIP_BETA = float(REG["actions.drip.betaAfter"])
DRIP_CONSUMPTION = float(REG["actions.drip.consumptionFactor"])
EXPAND_COST = float(REG["actions.expand.cost"])
EXPAND_FACTOR = float(REG["actions.expand.factor"])
TANK_RES = float(REG["basin.aquifer.tankResolution"])
ACTION_COST = {"orchard": ORCHARD_COST, "drip": DRIP_COST, "expand": EXPAND_COST}


@dataclass(frozen=True)
class Scheme:
    id: str
    seat: int
    area: float  # ha
    D: float  # Mm³, gross demand at intake
    K: float  # t at full demand
    ky: float
    p: float  # price relative to wheat (ADR 0007 §3)
    beta: float  # consumptive fraction
    N: float  # people (ADR 0007 §2)
    kappa: float
    actions: tuple
    goal: dict
    pump_factor: float
    wells_fail: float | None  # observed stock at or below which the wells deliver nothing


@dataclass(frozen=True)
class Basin:
    inflow: dict
    reserve: float
    B0: float
    Bmax: float | None  # None = unbounded (v1 reduction only, ADR 0006)
    Bres: float
    Blow: float
    r0: float
    rho: float  # ADR 0007 §4 return-flow recharge share
    kappa_loss: float  # ADR 0008 §6 baseflow loss per Mm³ below full
    seat_mult: tuple
    deck: dict
    cap_share: float
    cost_base: float
    cost_slope: float
    orchard: dict
    enabled: tuple


def load_scenario(variant: str = "full") -> tuple[Basin, list[Scheme]]:
    """variant 'full' = the shipped scenario; 'v1' = the §3 v1 reduction (A12)."""
    sc = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    b = sc["basin"]
    aq = b["aquifer"]
    pump = sc["actions"]["pump"]
    assert b["reserve"]["mode"] == "absolute"
    assert aq["gwSwCoupling"]["enabled"] and aq["surplusRecharge"] and aq["returnFlows"]
    basin = Basin(
        inflow={k: float(b["inflow"][k]) for k in ("wet", "normal", "dry")},
        reserve=float(b["reserve"]["value"]),
        B0=float(aq["initial"]),
        Bmax=float(aq.get("capacity", aq["initial"])),
        Bres=float(aq["reserve"]),
        Blow=float(aq["lowThreshold"]),
        r0=float(aq["naturalRecharge"]),
        rho=float(aq["returnRecharge"]),
        kappa_loss=float(aq["gwSwCoupling"]["lossPerMm3BelowFull"]),
        seat_mult=tuple(float(x) for x in aq["seatCostMultipliers"]),
        deck={k: int(v) for k, v in b["deck"].items()},
        cap_share=float(pump["capShare"]),
        cost_base=float(pump["costBase"]),
        cost_slope=float(pump["costSlope"]),
        orchard=dict(b["orchardCrop"]),
        enabled=tuple(lens["id"] for lens in sc["lenses"] if lens["enabled"]),
    )
    schemes = []
    for s in sc["schemes"]:
        d = s["derived"]
        schemes.append(
            Scheme(
                id=s["id"],
                seat=int(s["seat"]),
                area=float(s["areaHa"]),
                D=float(d["demandMm3"]),
                K=float(d["capacityT"]),
                ky=float(s["ky"]),
                p=float(s["price"]),
                beta=float(s["beta"]),
                N=float(s["people"]),
                kappa=float(s.get("kappa", 1.0)),
                actions=tuple(s["actions"]),
                goal=s["privateGoal"],
                pump_factor=float(s.get("pumpCostFactor", 1.0)),
                wells_fail=(float(s["wellsFailAtOrBelow"]) if "wellsFailAtOrBelow" in s else None),
            )
        )
        # Cross-check the file's derived values: D = area × depth, K = area × yield.
        assert abs(s["areaHa"] * s["depthMm"] * MM_HA_TO_MM3 - d["demandMm3"]) < 1e-6
        assert abs(s["areaHa"] * s["yieldTHa"] - d["capacityT"]) < 1e-6
    if variant == "v1":
        basin = replace(basin, r0=0.0, Bmax=None)
        schemes = [replace(s, beta=1.0) for s in schemes]
    return basin, schemes


# ---------------------------------------------------------------------------
# §2.4 Production
# ---------------------------------------------------------------------------


def yield_t(s: Scheme, W: float) -> float:
    """FAO-33 seasonal yield response with a linear fall below A = 0.5 (§2.4)."""
    A = W / s.D
    if A >= SURVIVAL:
        return s.K * (1.0 - s.ky * (1.0 - min(A, 1.0)))
    y_floor = s.K * (1.0 - s.ky * (1.0 - SURVIVAL))
    return y_floor * A / SURVIVAL


def marginal_values(s: Scheme) -> tuple[float, float]:
    """(below the kink, above the kink) value per Mm³, pᵢ·dYᵢ/dWᵢ (§3.4)."""
    below = s.p * s.K * (1.0 - s.ky * (1.0 - SURVIVAL)) / (SURVIVAL * s.D)
    above = s.p * s.K * s.ky / s.D
    return below, above


# ---------------------------------------------------------------------------
# §2.3 Allocation lenses: a generic claims solver + an exact value maximiser
# ---------------------------------------------------------------------------


def weighted_capped(claims, estate, weights) -> np.ndarray:
    """Qᵢ = min(Dᵢ, Cᵢ/Σ_U Cⱼ · AW^(k)), iterated over the uncapped set U (§2.3)."""
    claims = np.asarray(claims, float)
    weights = np.asarray(weights, float)
    if estate >= claims.sum() - EPS:
        return claims.copy()
    Q = np.zeros_like(claims)
    U = [i for i in range(len(claims)) if weights[i] > 0 and claims[i] > 0]
    rem = estate
    while U:
        w = weights[U]
        share = w / w.sum() * rem
        capped = [U[k] for k in range(len(U)) if share[k] >= claims[U[k]] - EPS]
        if not capped:
            Q[U] = share
            break
        for i in capped:
            Q[i] = claims[i]
            rem -= claims[i]
        U = [i for i in U if i not in capped]
    return Q


def cea(claims, estate) -> np.ndarray:
    return weighted_capped(claims, estate, np.ones(len(claims)))


def cel(claims, estate) -> np.ndarray:
    """Constrained equal losses: Σ max(0, Dᵢ − λ) = AW (§2.3), exact active set."""
    claims = np.asarray(claims, float)
    if estate >= claims.sum() - EPS:
        return claims.copy()
    active = list(range(len(claims)))
    while True:
        lam = (claims[active].sum() - estate) / len(active)
        drop = [i for i in active if claims[i] <= lam + EPS]
        if not drop:
            break
        active = [i for i in active if i not in drop]
    Q = np.zeros_like(claims)
    Q[active] = claims[active] - lam
    return Q


def talmud(claims, estate) -> np.ndarray:
    """Aumann–Maschler: CEA on half-claims if AW ≤ ½ΣD, else D/2 + CEL on half-claims."""
    half = np.asarray(claims, float) / 2.0
    if estate <= half.sum() + EPS:
        return cea(half, estate)
    return half + cel(half, estate - half.sum())


def proportional(claims, estate) -> np.ndarray:
    return weighted_capped(claims, estate, claims)


def max_value(schemes, budget, lower=None):
    """Exact maximiser of Σ pᵢYᵢ(Wᵢ) s.t. Σ Wᵢ ≤ budget, lowerᵢ ≤ Wᵢ ≤ Dᵢ (§2.3, A1).

    Y is piecewise linear with breakpoints 0, 0.5·D, D. Fix the segment of every
    scheme: the problem is an LP with one budget row, and an optimal vertex has
    at most one variable strictly inside its segment. So enumerate every
    combination of breakpoints for all schemes but one ("free"), give the free
    scheme the remaining budget (clipped to its bounds), and keep the best.
    Ties within 1e-9 are broken leximin in adequacy. Returns (W, tie_flag).
    """
    n = len(schemes)
    D = np.array([s.D for s in schemes])
    lo = np.zeros(n) if lower is None else np.asarray(lower, float)
    if budget >= D.sum() - EPS:
        return D.copy(), False
    cands = [sorted({lo[i], max(lo[i], SURVIVAL * D[i]), D[i]}) for i in range(n)]

    def value(W):
        return sum(s.p * yield_t(s, w) for s, w in zip(schemes, W, strict=False))

    best, best_v, ties = None, -math.inf, []
    for free in [None, *range(n)]:
        others = [i for i in range(n) if i != free]
        for combo in itertools.product(*(cands[i] for i in others)):
            W = np.zeros(n)
            W[others] = combo
            used = W.sum()
            if used > budget + EPS:
                continue
            if free is not None:
                rest = budget - used
                if rest < lo[free] - EPS:
                    continue
                W[free] = min(D[free], rest)
            v = value(W)
            if best is None or v > best_v + EPS * max(1.0, abs(best_v)):
                best, best_v, ties = W, v, [W]
            elif abs(v - best_v) <= EPS * max(1.0, abs(best_v)):
                ties.append(W)
    distinct = {tuple(np.round(t, 9)) for t in ties}
    if len(distinct) > 1:  # leximin in adequacy among the optimal vertices
        best = max(ties, key=lambda t: tuple(sorted(t / D)))
    return best, len(distinct) > 1


LENSES = [
    ("utilitarian", "Utilitarian"),
    ("weighted_utilitarian", "Weighted utilitarian"),
    ("egalitarian", "Strict egalitarian"),
    ("proportional", "Proportional"),
    ("capability", "Capability (κ = 1)"),
    ("sufficientarian", "Sufficientarian"),
    ("prioritarian", "Prioritarian (γ = 3 fixture)"),
    ("equal_sacrifice", "Equal sacrifice"),
    ("talmud", "Talmud"),
]
LENS_NAME = dict(LENSES)
UTIL_TIES: dict = {}


def allocate(lens: str, schemes, AW: float, gamma: float = PRIO_GAMMA_FIXTURE) -> np.ndarray:
    """River allocation Q under one §2.3 lens."""
    D = np.array([s.D for s in schemes])
    if lens == "utilitarian":
        Q, tie = max_value(schemes, AW)
        UTIL_TIES[("utilitarian", round(AW, 6))] = tie
        return Q
    if lens == "weighted_utilitarian":  # Cᵢ = pᵢKᵢ/Dᵢ (A2)
        return weighted_capped(D, AW, [s.p * s.K / s.D for s in schemes])
    if lens == "egalitarian":  # CEA on demands
        return cea(D, AW)
    if lens == "proportional":  # Cᵢ = Dᵢ
        return proportional(D, AW)
    if lens == "capability":  # Cᵢ = Nᵢκᵢ, capped
        return weighted_capped(D, AW, [s.N * s.kappa for s in schemes])
    if lens == "sufficientarian":  # A3
        floors = SUFF_FLOOR * D
        if floors.sum() >= AW - EPS:
            rule = {
                "proportional": proportional,
                "cea": cea,
                "cel": cel,
                "talmud": talmud,
                "capability": lambda c, e: weighted_capped(c, e, [s.N * s.kappa for s in schemes]),
            }
            return rule[SUFF_SCALING](floors, AW)
        assert SUFF_SECONDARY == "max_value", SUFF_SECONDARY
        Q, tie = max_value(schemes, AW, lower=floors)
        UTIL_TIES[("sufficientarian", round(AW, 6))] = tie
        return Q
    if lens == "prioritarian":  # Qᵢ ∝ wᵢ^(1/γ) Dᵢ^(1−1/γ), capped, w = 1
        return weighted_capped(D, AW, D ** (1.0 - 1.0 / gamma))
    if lens == "equal_sacrifice":
        return cel(D, AW)
    if lens == "talmud":
        return talmud(D, AW)
    raise ValueError(lens)


# ---------------------------------------------------------------------------
# §2.5 Indicators and §2.7 welfare functions
# ---------------------------------------------------------------------------


def one_minus_cv(x) -> float:
    x = np.asarray(x, float)
    return 1.0 - x.std(ddof=0) / x.mean()  # population SD (§2.5)


def gini_uncorrected(x) -> float:
    x = np.asarray(x, float)
    n = len(x)
    return np.abs(x[:, None] - x[None, :]).sum() / (2 * n * n * x.mean())


def welfare(schemes, A, gamma: float = WELFARE_GAMMA) -> dict:
    s = np.maximum(np.minimum(A, 1.0), SUPPLY_FLOOR)
    m = SURVIVAL
    N = np.array([sc.N for sc in schemes])
    n = len(s)
    pwf = float(np.sum(s ** (1 - gamma) / (1 - gamma)))
    ede = float(np.mean(s ** (1 - gamma)) ** (1 / (1 - gamma)))
    if np.any(s < m - EPS):
        swf = 0.0
    else:
        swf = (np.minimum(1, s / m).sum() + ((s - m) / (1 - m)).sum()) / (2 * n)
    return dict(
        UWF=float(s.mean()),
        PWF=pwf,
        PWF_EDE=ede,
        EWF=1 - gini_uncorrected(s),
        CWF=float((N * s).sum() / N.sum()),
        SWF=float(swf),
    )


def r3_of(S: float) -> float:
    return 1.0 - min(max((S - 1.0) / R3_RAMP, 0.0), 1.0)


def indicators(basin: Basin, schemes, Q, P, AW) -> dict:
    """§2.4 production, §2.5 indicators (ADR 0007 S with ρ), §2.7 welfare for one season."""
    Q = np.asarray(Q, float)
    P = np.asarray(P, float)
    W = Q + P
    D = np.array([s.D for s in schemes])
    K = np.array([s.K for s in schemes])
    p = np.array([s.p for s in schemes])
    beta = np.array([s.beta for s in schemes])
    area = np.array([s.area for s in schemes])
    N = np.array([s.N for s in schemes])
    A = W / D
    Y = np.array([yield_t(s, w) for s, w in zip(schemes, W, strict=False)])
    consumed = float((beta * W).sum())
    returned = float(((1 - beta) * W).sum())
    leaving = consumed + (1 - basin.rho) * returned  # ADR 0007 §7 numerator
    F = (float((p * Y).sum()) / consumed) / (float((p * K).sum()) / float((beta * D).sum()))
    F_div = (float((p * Y).sum()) / W.sum()) / (float((p * K).sum()) / D.sum())
    S = leaving / (AW + basin.r0)
    E_PJ = one_minus_cv(A)
    r1 = min(max(E_PJ, 0.0), 1.0)
    r2 = min(max(F, 0.0), 1.0)
    r3 = r3_of(S)
    return dict(
        Q=Q,
        P=P,
        W=W,
        A=A,
        Y=Y,
        Dvec=D,
        pY=p * Y,
        value=float((p * Y).sum()),
        SY=float(Y.sum()),
        E_PJ=E_PJ,
        E_SE=one_minus_cv(W),
        E_SE_ha=one_minus_cv(W / area),
        E_SE_N=one_minus_cv(W / N),
        F=F,
        F_div=F_div,
        S=S,
        r1=r1,
        r2=r2,
        r3=r3,
        score=(r1 * r2 * r3) ** (1 / 3),
        consumed=consumed,
        returned=returned,
        leaving=leaving,
        **welfare(schemes, A),
    )


# ---------------------------------------------------------------------------
# §2.6 Aquifer (ADR 0006, 0007, 0008), pumps, costs, baseflow
# ---------------------------------------------------------------------------


def observed(B: float) -> float:
    """ADR 0004: the observed level is the stock floored to the tank resolution (A7)."""
    return math.floor(B / TANK_RES + EPS) * TANK_RES


def pump_capacity(basin: Basin, s: Scheme, B: float) -> float:
    """ADR 0008 §3, §5: capShare × D; 0 once the observed stock is at or below the wells' limit."""
    if s.wells_fail is not None and observed(B) <= s.wells_fail + EPS:
        return 0.0
    return basin.cap_share * s.D


def pump_cost(basin: Basin, s: Scheme, B: float) -> float:
    """c = factor × (base + slope·max(0, 1 − B_obs/B₀)) × seat multiplier once B_obs < B_low (A9)."""
    Bo = observed(B)
    c = s.pump_factor * (basin.cost_base + basin.cost_slope * max(0.0, 1.0 - Bo / basin.B0))
    if Bo < basin.Blow:
        c *= basin.seat_mult[s.seat - 1]
    return c


def baseflow_loss(basin: Basin, B_next: float) -> float:
    """ADR 0008 §6: next season's inflow falls by κ·max(0, B₀ − B_obs) (A10)."""
    return basin.kappa_loss * max(0.0, basin.B0 - observed(B_next))


def ration(basin: Basin, B: float, req) -> np.ndarray:
    """Pro-rata cut of requests to the stock above B_res (§2.6, A7)."""
    req = np.asarray(req, float)
    avail = max(0.0, B - basin.Bres)
    if req.sum() > avail + EPS:
        return req * (avail / req.sum())
    return req.copy()


def aquifer_step(basin: Basin, B: float, AW: float, Q, P, W, betas) -> dict:
    """B_{t+1} = min(B_max, max(B_res, B + surplus + r₀ + ρΣ(1−β)W − ΣP)); spill = excess."""
    surplus = AW - float(np.sum(Q))
    assert surplus >= -EPS, surplus
    ret_each = (1 - np.asarray(betas)) * np.asarray(W)
    ret = float(ret_each.sum())
    unbounded = B + surplus + basin.r0 + basin.rho * ret - float(np.sum(P))
    floored = max(basin.Bres, unbounded)
    assert floored - unbounded <= EPS, "B_res floor bound: rationing reading A7 violated"
    B_next = floored if basin.Bmax is None else min(basin.Bmax, floored)
    return dict(
        B_next=B_next,
        spill=floored - B_next,
        surplus=surplus,
        ret=ret,
        ret_each=ret_each,
        recharge_ret=basin.rho * ret,
        river_ret=(1 - basin.rho) * ret,
    )


# ---------------------------------------------------------------------------
# Actions (§4.3, ADR 0007 §6, §8), effective from t+1
# ---------------------------------------------------------------------------


def apply_action(basin: Basin, s: Scheme, action: str) -> Scheme:
    assert action in s.actions, f"{s.id} may not play {action} (ADR 0007 §5)"
    if action == "orchard":  # A14
        o = basin.orchard
        return replace(
            s,
            D=s.area * float(o["depthMm"]) * float(o["beta"]) / s.beta * MM_HA_TO_MM3,
            K=s.area * float(o["yieldTHa"]),
            ky=float(o["ky"]),
            p=float(o["price"]),
        )
    if action == "drip":  # A13
        C = DRIP_CONSUMPTION * s.beta * s.D
        return replace(s, D=C / DRIP_BETA, beta=DRIP_BETA)
    if action == "expand":
        f = EXPAND_FACTOR
        return replace(s, area=s.area * f, D=s.D * f, K=s.K * f)
    raise ValueError(action)


# ---------------------------------------------------------------------------
# Season loop
# ---------------------------------------------------------------------------

CHECKS: list[dict] = []  # every computed season, for the self-check section


def check_balance(case: str, basin: Basin, AW, Q, ind, B, step, P=None, caps=None, quiet=False) -> None:
    surplus_ok = abs(float(np.sum(Q)) + step["surplus"] - AW) < 1e-9
    lhs = AW + basin.r0 - ind["consumed"] - (1 - basin.rho) * ind["returned"]  # ADR 0007 §7
    rhs = (step["B_next"] - B) + step["spill"]
    ok_rat = True if P is None else (B - float(np.sum(P)) >= basin.Bres - 1e-9)
    ok_cap = True if caps is None else bool(np.all(np.asarray(P) <= np.asarray(caps) + 1e-9))
    D = ind["Dvec"]
    ok_q = bool(np.all(Q >= -EPS) and np.all(Q <= D + EPS))
    ok = surplus_ok and abs(lhs - rhs) < 1e-9 and ok_rat and ok_cap and ok_q
    CHECKS.append(
        dict(
            case=case,
            AW=AW,
            sumQ=float(np.sum(Q)),
            surplus=step["surplus"],
            lhs=lhs,
            dB=step["B_next"] - B,
            spill=step["spill"],
            ok=ok,
            quiet=quiet,
            ok_rat=ok_rat,
            ok_cap=ok_cap,
        )
    )
    assert surplus_ok, case
    assert abs(lhs - rhs) < 1e-9, (case, lhs, rhs)
    assert ok_rat, ("rationing drew below B_res", case)
    assert ok_cap, ("pump cap exceeded", case)
    assert ok_q, ("0 ≤ Q ≤ D violated", case)


def run_game(
    basin, schemes, cards, lens="proportional", pump="none", actions=None, case="game", gamma=PRIO_GAMMA_FIXTURE, quiet=False
):
    """Rounds in order. pump: 'none' or 'full' (every scheme requests its full capacity)."""
    B = basin.B0
    loss = 0.0
    out = []
    for t, card in enumerate(cards):
        inflow = basin.inflow[card] - loss
        AW = inflow - basin.reserve
        Q = allocate(lens, schemes, AW, gamma)
        Bo = observed(B)
        caps = np.array([pump_capacity(basin, s, B) for s in schemes])
        req = caps.copy() if pump == "full" else np.zeros(len(schemes))
        P = ration(basin, B, req)
        cost = np.array([pump_cost(basin, s, B) for s in schemes])
        ind = indicators(basin, schemes, Q, P, AW)
        step = aquifer_step(basin, B, AW, Q, P, ind["W"], [s.beta for s in schemes])
        check_balance(f"{case} r{t + 1} ({card})", basin, AW, Q, ind, B, step, P, caps, quiet)
        act = (actions or {}).get(t, {})
        act_cost = np.array([ACTION_COST[act[s.id]] if s.id in act else 0.0 for s in schemes])
        dL = ind["pY"] / 100 - cost * P - act_cost
        out.append(
            dict(
                t=t + 1,
                card=card,
                inflow=inflow,
                loss_in=loss,
                AW=AW,
                B=B,
                B_obs=Bo,
                caps=caps,
                req=req,
                rationed=bool(np.any(P < req - EPS)),
                cost=cost,
                dL=dL,
                act_cost=act_cost,
                D=[s.D for s in schemes],
                K=[s.K for s in schemes],
                p=[s.p for s in schemes],
                ky=[s.ky for s in schemes],
                beta=[s.beta for s in schemes],
                area=[s.area for s in schemes],
                potential=[s.p * s.K / 100 for s in schemes],
                **ind,
                **step,
            )
        )
        B = step["B_next"]
        loss = baseflow_loss(basin, B)
        schemes = [apply_action(basin, s, act[s.id]) if s.id in act else s for s in schemes]
    return out, schemes


def static_case(basin, schemes, card, lens, gamma=PRIO_GAMMA_FIXTURE, label=""):
    AW = basin.inflow[card] - basin.reserve
    Q = allocate(lens, schemes, AW, gamma)
    P = np.zeros(len(schemes))
    ind = indicators(basin, schemes, Q, P, AW)
    step = aquifer_step(basin, basin.B0, AW, Q, P, ind["W"], [s.beta for s in schemes])
    check_balance(label or f"{card} {lens}", basin, AW, Q, ind, basin.B0, step)
    return dict(AW=AW, **ind, **step)


# ---------------------------------------------------------------------------
# Printing helpers (rounding happens only here)
# ---------------------------------------------------------------------------


def _q(x: float, nd: int) -> Decimal:
    """Round half away from zero on the shortest decimal repr (print only)."""
    return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def fn(x: float, nd: int) -> str:
    v = _q(x, nd)
    s = f"{abs(v):,.{nd}f}"
    return ("−" + s) if v < 0 and float(v) != 0.0 else s


def f2(x: float) -> str:
    return fn(x, 2)


def f1(x: float) -> str:
    return fn(x, 1)


def t0(x: float) -> str:
    return fn(x, 0)


def pwf_fmt(x: float) -> str:
    """PWF₃ as §3.1 prints it: one decimal from |x| ≥ 10, two below."""
    return f1(x) if abs(x) >= 10 else f2(x)


def swf_fmt(x: float) -> str:
    return "0" if abs(x) < EPS else f2(x)


def trio(xs, fmt=f2) -> str:
    return " / ".join(fmt(x) for x in xs)


def table(header, rows) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# §3.1 / §3.2 static tables, wet-year sentence
# ---------------------------------------------------------------------------


def lens_rows(card: str):
    bv, sv = load_scenario("v1")
    bf, sf = load_scenario("full")
    lenses = [*list(LENSES), ("prioritarian_g2", f"Prioritarian (γ = {PRIO_GAMMA_DEFAULT:g}, registry default)")]
    rows = []
    for key, name in lenses:
        lens, g = ("prioritarian", PRIO_GAMMA_DEFAULT) if key == "prioritarian_g2" else (key, PRIO_GAMMA_FIXTURE)
        v1 = static_case(bv, sv, card, lens, g, f"§3 {card} {key} v1")
        fs = static_case(bf, sf, card, lens, g, f"§3 {card} {key} full")
        assert np.allclose(v1["Q"], fs["Q"]) and np.allclose(v1["Y"], fs["Y"])  # §3: β cancels
        rows.append((key, name, v1, fs))
    return rows


def coincidences(rows) -> list[str]:
    out, seen = [], set()
    for i, (k1, n1, a, _) in enumerate(rows):
        if k1 in seen:
            continue
        same = [(k2, n2) for (k2, n2, b, _) in rows[i + 1 :] if np.allclose(a["Q"], b["Q"], atol=1e-9)]
        if same:
            seen.update(k for k, _ in same)
            out.append(f"{n1} = " + " = ".join(n for _, n in same))
    return out


def print_static(card: str, with_welfare: bool) -> list:
    rows = lens_rows(card)
    AW = rows[0][2]["AW"]
    head = ["Lens", "Q A / B / C", "A A / B / C", "Y A / B / C (t)", "ΣY", "Σ pY", "E_PJ", "E_SE", "F"]
    if with_welfare:
        head.append("UWF / PWF₃ / EWF / CWF / SWF")
    head += ["F (full)", "S (full)", "r₃ (full)", "score (full)"]
    body = []
    for _key, name, v1, fs in rows:
        assert abs(v1["S"] - min(1.0, v1["W"].sum() / AW)) < 1e-9
        r = [
            name,
            trio(v1["Q"]),
            trio(v1["A"]),
            trio(v1["Y"], t0),
            t0(v1["SY"]),
            t0(v1["value"]),
            f2(v1["E_PJ"]),
            f2(v1["E_SE"]),
            f2(v1["F"]),
        ]
        if with_welfare:
            w = v1
            pwf = pwf_fmt(w["PWF"])
            r.append(f"{f2(w['UWF'])} / {pwf} / {f2(w['EWF'])} / {f2(w['CWF'])} / {f2(w['SWF'])}")
        r += [f2(fs["F"]), f2(fs["S"]), f2(fs["r3"]), f2(fs["score"])]
        body.append(r)
    title = "Dry" if card == "dry" else "Normal"
    print(f"### §3.{1 if card == 'dry' else 2} {title} year, AW = {f2(AW)}\n")
    print(
        "Columns Q … F (and welfare): v1 reduction (β = 1, r₀ = 0, no pumping, no actions). "
        "Columns marked (full): the scenario's β, r₀, ρ and capacity, from B₀; same Q, A, Y.\n"
    )
    print(table(head, body))
    print()
    s_v1 = sorted({round(v1["S"], 12) for _, _, v1, _ in rows})
    print(f"S under the v1 reduction: {', '.join(f2(x) for x in s_v1)} in every row (r₃ = 1).\n")
    co = coincidences(rows)
    print("Coincidences (identical Q): " + ("; ".join(co) if co else "none") + ".\n")
    ties = {k: v for k, v in UTIL_TIES.items() if v and abs(k[1] - AW) < 1e-6}
    print("Value-maximiser ties: " + (str(ties) if ties else "none") + ".\n")
    return rows


def print_wet():
    rows = lens_rows("wet")
    ref = rows[0][2]
    for _, _, v1, _fs in rows:
        assert np.allclose(v1["Q"], ref["Q"])
    _, _, v1, fs = rows[0]
    basin, _ = load_scenario("full")
    print("### Wet year (sentence values)\n")
    print(
        f"Wet year (AW = {f2(v1['AW'])}): every lens gives Q = {trio(v1['Q'])}, "
        f"{f2(v1['surplus'])} Mm³ to the aquifer, A = {trio(v1['A'])}, ΣY = {t0(v1['SY'])} t "
        f"(Σ pY = {t0(v1['value'])}), E_PJ = {f2(v1['E_PJ'])}, E_SE = {f2(v1['E_SE'])}, "
        f"F = {f2(v1['F'])}, S = {f2(v1['S'])} (v1 reduction). Full scenario: F = {f2(fs['F'])}, "
        f"S = {f2(fs['S'])}, r₃ = {f2(fs['r3'])}, score = {f2(fs['score'])}; recharge = surplus "
        f"{f2(fs['surplus'])} + r₀ {f2(basin.r0)} + ρ·Σ(1−β)W {f2(fs['recharge_ret'])}; aquifer "
        f"{f2(fs['B_next'])} after the season with spill {f2(fs['spill'])} Mm³ "
        f"(capacity {f2(basin.Bmax)}).\n"
    )


# ---------------------------------------------------------------------------
# §3.3 dynamic fixtures (full scenario)
# ---------------------------------------------------------------------------


def fixture_pumping():
    print("#### (a) Pumping — normal, proportional, every scheme pumps its full capacity\n")
    basin, sch = load_scenario("full")
    (s,), _ = run_game(basin, sch, ["normal"], pump="full", case="pumping")
    print(
        table(
            ["W A / B / C", "A A / B / C", "ΣY", "Σ pY", "F", "S", "r₃", "score", "B next", "spill"],
            [
                [
                    trio(s["W"]),
                    trio(s["A"]),
                    t0(s["SY"]),
                    t0(s["value"]),
                    f2(s["F"]),
                    f2(s["S"]),
                    f2(s["r3"]),
                    f2(s["score"]),
                    f2(s["B_next"]),
                    f2(s["spill"]),
                ]
            ],
        )
    )
    print()
    print(
        table(
            ["Scheme", "Q", "capacity = P", "cost per Mm³", "pump cost", "pY/100", "ΔL"],
            [
                [
                    x.id,
                    f2(s["Q"][i]),
                    f2(s["P"][i]),
                    f2(s["cost"][i]),
                    f2(s["cost"][i] * s["P"][i]),
                    f2(s["pY"][i] / 100),
                    f2(s["dL"][i]),
                ]
                for i, x in enumerate(sch)
            ],
        )
    )
    print()


def fixture_depletion():
    deck = ["dry", "dry", "normal", "normal", "wet", "dry"]
    basin, sch = load_scenario("full")
    print(f"#### (b) Selfish depletion — {', '.join(deck)}; proportional; every scheme pumps its full capacity each round\n")
    out, _ = run_game(basin, sch, deck, pump="full", case="selfish")
    rows = []
    for s in out:
        rows.append(
            [
                str(s["t"]),
                s["card"],
                f2(s["loss_in"]),
                f2(s["AW"]),
                f2(s["B"]),
                f2(s["B_obs"]),
                trio(s["caps"]),
                trio(s["P"]) + (" (rationed)" if s["rationed"] else ""),
                trio(s["cost"]),
                trio(s["dL"]),
                f2(s["B_next"]),
                f2(s["spill"]),
                f2(s["S"]),
                f2(s["r3"]),
            ]
        )
    print(
        table(
            [
                "Round",
                "Card",
                "inflow loss",
                "AW",
                "B start",
                "B obs",
                "caps A / B / C",
                "P A / B / C",
                "cost per Mm³ A / B / C",
                "ΔL A / B / C",
                "B next",
                "spill",
                "S",
                "r₃",
            ],
            rows,
        )
    )
    print()
    iB = next(i for i, x in enumerate(sch) if x.wells_fail is not None)
    fail = next((s["t"] for s in out if s["caps"][iB] == 0.0), None)
    last = out[-1]["B_next"]
    print(
        f"Paddy ({sch[iB].id}) wells first fail (capacity 0, observed level ≤ "
        f"{f2(sch[iB].wells_fail)}) in round {fail}. After round {len(out)}: B = {f2(last)}, "
        f"observed {f2(observed(last))}, next inflow loss {f2(baseflow_loss(basin, last))}.\n"
    )
    return out


def fixture_cooperative():
    deck = ["dry", "dry", "normal", "normal", "wet", "dry"]
    basin, sch = load_scenario("full")
    print("#### (c) Same deck, no pumping (cooperative), proportional\n")
    out, _ = run_game(basin, sch, deck, case="cooperative")
    print(
        table(
            ["Round", "Card", "inflow loss", "AW", "B start", "B next", "spill", "S"],
            [
                [
                    str(s["t"]),
                    s["card"],
                    f2(s["loss_in"]),
                    f2(s["AW"]),
                    f2(s["B"]),
                    f2(s["B_next"]),
                    f2(s["spill"]),
                    f2(s["S"]),
                ]
                for s in out
            ],
        )
    )
    print()


def fixture_return_flow():
    print("#### (d) Return flow — normal, proportional, no pumping\n")
    basin, sch = load_scenario("full")
    (s,), _ = run_game(basin, sch, ["normal"], case="return flow")
    print(
        f"Σ(1 − βᵢ)Wᵢ = {' + '.join(f2(x) for x in s['ret_each'])} = {f2(s['ret'])} Mm³; "
        f"ρ = {basin.rho:g}: to the aquifer ρ·Σ = {f2(s['recharge_ret'])}, to the river below the "
        f"off-takes (1 − ρ)·Σ = {f2(s['river_ret'])}. Plus r₀ = {f2(basin.r0)} and surplus "
        f"{f2(s['surplus'])}: B {f2(s['B'])} → {f2(s['B_next'])}, spill {f2(s['spill'])} "
        f"(unbounded balance {f2(s['B_next'] + s['spill'])}); S = {f2(s['S'])}.\n"
    )


def fixture_baseflow():
    print(f"#### (e) Baseflow loss next season (κ = {load_scenario()[0].kappa_loss:g} per Mm³ below full, observed level)\n")
    basin, _ = load_scenario("full")
    print(
        table(
            ["B after season", "observed", "next inflow loss (Mm³)"],
            [[f2(b), f2(observed(b)), f2(baseflow_loss(basin, b))] for b in (20, 18, 15, 12, 10)],
        )
    )
    print()


def fixture_orchard():
    basin, sch = load_scenario("full")
    who = next(s.id for s in sch if "orchard" in s.actions)
    others = [s.id for s in sch if "orchard" in s.actions and s.id != who]
    print(
        f"#### (f) Orchard — {who} plays Orchard in round 2 (normal ×3, proportional, no pumping; "
        f"also allowed: {', '.join(others) or 'none'})\n"
    )
    out, _ = run_game(basin, sch, ["normal"] * 3, actions={1: {who: "orchard"}}, case="orchard")
    i = [s.id for s in sch].index(who)
    print(
        table(
            [
                "Round",
                f"D_{who}",
                f"K_{who}",
                f"p_{who}",
                f"Kᵧ_{who}",
                f"β_{who}",
                f"Q_{who}",
                f"A_{who}",
                f"pY_{who}/100",
                "action cost",
                f"ΔL_{who}",
                "ΣD",
                "S",
            ],
            [
                [
                    str(s["t"]),
                    f2(s["D"][i]),
                    t0(s["K"][i]),
                    f2(s["p"][i]),
                    f2(s["ky"][i]),
                    f2(s["beta"][i]),
                    f2(s["Q"][i]),
                    f2(s["A"][i]),
                    f2(s["pY"][i] / 100),
                    f2(s["act_cost"][i]),
                    f2(s["dL"][i]),
                    f2(sum(s["D"])),
                    f2(s["S"]),
                ]
                for s in out
            ],
        )
    )
    print()


def fixture_drip_expand():
    basin, sch = load_scenario("full")
    who = next(s.id for s in sch if "drip" in s.actions)
    print(f"#### (g) Drip then Expand — {who}: Drip round 1, Expand round 2 (normal ×3, proportional, no pumping)\n")
    out, _ = run_game(basin, sch, ["normal"] * 3, actions={0: {who: "drip"}, 1: {who: "expand"}}, case="drip-expand")
    i = [s.id for s in sch].index(who)
    print(
        table(
            [
                "Round",
                f"D_{who}",
                f"K_{who}",
                f"β_{who}",
                f"area_{who}",
                f"β·D_{who}",
                f"W_{who}",
                f"(1−β)W_{who}",
                f"ΔL_{who}",
                "ΣD",
                "B next",
                "S",
            ],
            [
                [
                    str(s["t"]),
                    f2(s["D"][i]),
                    t0(s["K"][i]),
                    f2(s["beta"][i]),
                    t0(s["area"][i]),
                    f2(s["beta"][i] * s["D"][i]),
                    f2(s["W"][i]),
                    f2(s["ret_each"][i]),
                    f2(s["dL"][i]),
                    f2(sum(s["D"])),
                    f2(s["B_next"]),
                    f2(s["S"]),
                ]
                for s in out
            ],
        )
    )
    print()


def fixture_equalisandum():
    basin, sch = load_scenario("full")
    r = static_case(basin, sch, "dry", "proportional", label="equalisandum")
    print("#### (h) Equalisandum — dry, proportional\n")
    print(
        f"E_SE per claimant {f2(r['E_SE'])}; per hectare {f2(r['E_SE_ha'])} (E_PJ = {f2(r['E_PJ'])}); "
        f"per person {f2(r['E_SE_N'])}.\n"
    )


def verdict(sch, AW, A_real, voted, pool):
    D = np.array([s.D for s in sch])
    d = {}
    for key in pool:
        g = PRIO_GAMMA_DEFAULT if key == "prioritarian" else PRIO_GAMMA_FIXTURE
        d[key] = float(np.abs(A_real - allocate(key, sch, AW, g) / D).sum())
    m = min(d.values())
    tied = [k for k, v in d.items() if v <= m + 1e-9]
    return (voted if voted in tied else tied[0]), tied, m


def fixture_verdict(dry_rows):
    print("#### (i) Verdicts — dry year, no pumping\n")
    basin, sch = load_scenario("full")
    AW = basin.inflow["dry"] - basin.reserve
    cols = ["UWF", "PWF", "EWF", "CWF", "SWF"]
    nine = dry_rows[: len(LENSES)]
    names = [n for _, n, _, _ in nine]
    vals = {c: [r[2][c] for r in nine] for c in cols}
    for voted in ("proportional", "utilitarian"):
        i = [k for k, _ in LENSES].index(voted)
        A = nine[i][2]["A"]
        v9, t9, d9 = verdict(sch, AW, A, voted, [k for k, _ in LENSES])
        ve, te, _de = verdict(sch, AW, A, voted, list(basin.enabled))
        ranks = []
        for c in cols:
            v = vals[c][i]
            rank = 1 + sum(1 for x in vals[c] if x > v + 1e-12)
            ties = sum(1 for x in vals[c] if abs(x - v) <= 1e-12)
            ranks.append(f"{c} {f2(v)} rank {rank}/{len(names)}" + (f" (tied ×{ties})" if ties > 1 else ""))
        print(
            f"- {LENS_NAME[voted]} voted: verdict (nine lenses) = {LENS_NAME[v9]} "
            f"(Σ|A − A*| = {f2(d9)}; tied: {', '.join(LENS_NAME[k] for k in t9)}); verdict (enabled lenses) "
            f"= {LENS_NAME[ve]} (tied: {', '.join(LENS_NAME[k] for k in te)}); pumping gap 0. " + "; ".join(ranks) + "."
        )
    top = {c: names[int(np.argmax(vals[c]))] for c in cols}
    print("- Highest per column over the nine lenses: " + "; ".join(f"{c}: {n}" for c, n in top.items()) + ".\n")


def fixture_prioritarian_limits():
    print("#### (j) Prioritarian limits\n")
    basin, sch = load_scenario("full")
    rows = []
    for card in ("dry", "normal"):
        AW = basin.inflow[card] - basin.reserve
        lo = np.abs(allocate("prioritarian", sch, AW, 1.001) - allocate("egalitarian", sch, AW)).max()
        hi = np.abs(allocate("prioritarian", sch, AW, 1000.0) - allocate("proportional", sch, AW)).max()
        rows.append([card, f"{lo:.4f}", f"{hi:.4f}"])
    print(table(["Card", "max |Q(γ=1.001) − Q(egalitarian)|", "max |Q(γ=1000) − Q(proportional)|"], rows))
    print()


def goal_met(s: Scheme, out, i) -> bool:
    g = s.goal
    A = np.array([o["A"][i] for o in out])
    if g["kind"] == "livelihood_share":
        return sum(o["dL"][i] for o in out) >= g["threshold"] * sum(o["potential"][i] for o in out) - EPS
    if g["kind"] == "adequacy_floor":
        return bool(A.min() >= g["threshold"] - EPS)
    if g["kind"] == "adequacy_in_half_seasons":
        return 2 * int(np.sum(A >= g["threshold"] - EPS)) >= len(A)
    raise ValueError(g["kind"])


def fixture_goals():
    basin, sch = load_scenario("full")
    deck = [c for c in ("wet", "normal", "dry") for _ in range(basin.deck[c])]
    orders6 = sorted(set(itertools.permutations(deck)))
    orders5 = sorted({o[:5] for o in orders6})
    print(
        f"#### (k) Goal attainability — all-principled, no pumping; T = 6: {len(orders6)} distinct "
        f"orders of {basin.deck['wet']}W/{basin.deck['normal']}N/{basin.deck['dry']}D; T = 5: "
        f"{len(orders5)} distinct five-card sequences\n"
    )
    lens_set = [*list(LENSES), ("prioritarian_g2", f"Prioritarian (γ = {PRIO_GAMMA_DEFAULT:g})")]
    rows = []
    for key, name in lens_set:
        lens, g = ("prioritarian", PRIO_GAMMA_DEFAULT) if key == "prioritarian_g2" else (key, PRIO_GAMMA_FIXTURE)
        cells = []
        for orders in (orders6, orders5):
            met = np.zeros(len(sch))
            alll = 0
            extra = []
            for o in orders:
                out, _ = run_game(basin, sch, list(o), lens=lens, gamma=g, case=f"goals {key}", quiet=True)
                m = [goal_met(s, out, i) for i, s in enumerate(sch)]
                met += m
                alll += all(m)
                extra.append(out[-1]["B_next"])
            assert min(extra) >= basin.B0 - EPS  # no pumping: the aquifer stays full (A15)
            cells.append(
                " / ".join(f"{100 * x / len(orders):.0f} %" for x in met) + f" (all: {100 * alll / len(orders):.0f} %)"
            )
        en = "yes" if lens in basin.enabled else "no"
        rows.append([name, en, cells[0], cells[1]])
    print(table(["Lens", "enabled", "T = 6: goal met A / B / C", "T = 5: goal met A / B / C"], rows))
    print()
    # The A goal numbers under proportional for the full deck (order-independent here)
    out, _ = run_game(basin, sch, deck, case="goals detail", quiet=True)
    iA = 0
    share = sum(o["dL"][iA] for o in out) / sum(o["potential"][iA] for o in out)
    print(
        f"Proportional, full deck: {sch[iA].id} reaches {f2(100 * share)} % of its full-demand potential "
        f"(goal ≥ {f2(100 * sch[iA].goal['threshold'])} %).\n"
    )


def cross_checks():
    print("### §3.4 Cross-checks: marginal value and pump cost (full scenario)\n")
    basin, sch = load_scenario("full")
    rows = []
    for s in sch:
        below, above = marginal_values(s)
        rows.append(
            [
                s.id,
                f2(s.p),
                t0(s.K * s.ky / s.D),
                t0(above),
                f2(above / 100),
                t0(s.K * (1 - s.ky * (1 - SURVIVAL)) / (SURVIVAL * s.D)),
                t0(below),
                f2(below / 100),
            ]
        )
    print(
        table(
            [
                "Scheme",
                "p",
                "K·Kᵧ/D (t/Mm³)",
                "p·K·Kᵧ/D",
                "points/Mm³ above kink",
                "Y(0.5)/(0.5D) (t/Mm³)",
                "p·Y(0.5)/(0.5D)",
                "points/Mm³ below kink",
            ],
            rows,
        )
    )
    print()
    rows = []
    for B in (20, 15, 12, 10):
        rows.append(
            [f2(B)]
            + [f2(pump_cost(basin, s, B)) + ("" if pump_capacity(basin, s, B) > 0 else " (wells failed)") for s in sch]
        )
    print(table(["B (observed)", *[f"cost per Mm³ {s.id} (factor {s.pump_factor:g})" for s in sch]], rows))
    print()


# ---------------------------------------------------------------------------
# Self-check and main
# ---------------------------------------------------------------------------


def self_check():
    print("### Self-check\n")
    basin, sch = load_scenario("full")
    D = np.array([s.D for s in sch])
    for AW in (9.0, 10.0, 15.0, 20.0):
        for key, _ in LENSES:
            for g in (PRIO_GAMMA_FIXTURE, PRIO_GAMMA_DEFAULT):
                Q = allocate(key, sch, AW, g)
                assert np.all(Q >= -EPS) and np.all(Q <= D + EPS), key
                assert abs(Q.sum() - min(AW, D.sum())) < 1e-9, (key, AW)
    for AW in (10.0, 15.0):
        Wx, _ = max_value(sch, AW)
        vx = sum(s.p * yield_t(s, w) for s, w in zip(sch, Wx, strict=False))
        best = -1.0
        for a in np.arange(0, D[0] + 1e-9, 0.01):
            for b in np.arange(0, min(D[1], AW - a) + 1e-9, 0.01):
                c = min(D[2], AW - a - b)
                if c < -1e-9:
                    continue
                v = sch[0].p * yield_t(sch[0], a) + sch[1].p * yield_t(sch[1], b) + sch[2].p * yield_t(sch[2], c)
                best = max(best, v)
        assert vx >= best - 1e-6, (AW, vx, best)
    # Rationing: random requests at stocks near the reserve never draw below it.
    rng = np.random.default_rng(0)
    for _ in range(2000):
        B = basin.Bres + rng.uniform(0, 3)
        req = rng.uniform(0, 5, size=3)
        P = ration(basin, B, req)
        assert B - P.sum() >= basin.Bres - 1e-9 and np.all(P <= req + 1e-12)
    n_ok = sum(c["ok"] for c in CHECKS)
    print(
        "Lens feasibility (0 ≤ Q ≤ D, ΣQ = min(AW, ΣD)) at AW = 9, 10, 15, 20 (γ = 3 and 2): passed. "
        "Exact value maximiser ≥ 0.01-grid brute force at AW = 10, 15: passed. Rationing never draws "
        "below B_res (2,000 random requests, and every played round): passed. Pumps ≤ capacity in every "
        "played round: passed.\n"
    )
    print(
        f"Every computed season: ΣQ + surplus = AW; AW + r₀ − ΣβW − (1 − ρ)Σ(1 − β)W = ΔB + spill; "
        f"0 ≤ Q ≤ D; B − ΣP ≥ B_res; P ≤ capacity: {n_ok}/{len(CHECKS)} pass (B_res floor never bound).\n"
    )
    rows = [
        [
            c["case"],
            f2(c["AW"]),
            f2(c["sumQ"]),
            f2(c["surplus"]),
            f2(c["lhs"]),
            f2(c["dB"]),
            f2(c["spill"]),
            "ok" if c["ok"] else "FAIL",
        ]
        for c in CHECKS
        if not c["case"].startswith("§3") and not c["quiet"]
    ]
    print(table(["Case", "AW", "ΣQ", "surplus", "AW + r₀ − ΣβW − (1−ρ)Σ(1−β)W", "ΔB", "spill", ""], rows))
    print()


# ---------------------------------------------------------------------------
# Blueprint §3 text (Markdown ready to paste)
# ---------------------------------------------------------------------------


def lname(name: str) -> str:
    """Lens name inside a sentence: lower case except proper nouns."""
    return name if name.startswith("Talmud") else name[0].lower() + name[1:]


def pct(x: float) -> str:
    return f"{fn(100 * x, 0)} %"


def rounds_txt(rs) -> str:
    if not rs:
        return "none"
    if len(rs) > 1 and rs == list(range(rs[0], rs[-1] + 1)):
        return f"{rs[0]}–{rs[-1]}"
    return ", ".join(map(str, rs))


def goal_rates(lens, gamma, orders, basin, sch):
    met = np.zeros(len(sch))
    alll = 0
    for o in orders:
        out, _ = run_game(basin, sch, list(o), lens=lens, gamma=gamma, case=f"bp goals {lens}", quiet=True)
        m = [goal_met(s, out, i) for i, s in enumerate(sch)]
        met += m
        alll += all(m)
    return met / len(orders), alll / len(orders)


def blueprint_text():
    bv, sv = load_scenario("v1")
    bf, sf = load_scenario("full")
    ids = [s.id for s in sf]
    names = dict(LENSES)
    L: list[str] = []
    w = L.append

    # ---- intro and wet sentence (v1 values)
    wet = static_case(bv, sv, "wet", "proportional", label="bp wet v1")
    for key, _ in LENSES:
        assert np.allclose(static_case(bv, sv, "wet", key, label=f"bp wet {key}")["Q"], wet["Q"])
    assert np.allclose(wet["A"], 1.0)
    AWw = bv.inflow["wet"] - bv.reserve
    w("## 3. Reference vectors and fixtures")
    w("")
    w(
        "Computed from §2 for the Kelvara basin (§2.2; ADR 0007, ADR 0008) by an independent reference "
        "implementation, `packages/engine-py/analysis/reference_model.py`, written from this specification "
        "without importing the engine. §3.1 and §3.2 use the v1 reduction of §2.6: **β = 1, r₀ = 0, no "
        "pumping, no actions** (and no aquifer capacity). Allocations Q, adequacies A, yields Y, E\\_PJ and "
        "E\\_SE do not depend on β, so the tables are the allocation truth for every version and the scoring "
        "truth (F, S) for the v1 reduction only. The dynamic fixtures of §3.3 and the cross-checks of §3.4 use "
        f"the full scenario: β = {trio([s.beta for s in sf])}, r₀ = {bf.r0:g}, ρ = {bf.rho:g}, "
        f"B₀ = B\\_max = {bf.B0:g}, B\\_low = {bf.Blow:g}, B\\_res = {bf.Bres:g}, pump capacity "
        f"{bf.cap_share:g} × D, cost fᵢ({bf.cost_base:g} + {bf.cost_slope:g}·max(0, 1 − B/B₀)) per Mm³ on the "
        f"observed level, baseflow loss {bf.kappa_loss:g}(B₀ − B), one season per year. Values are rounded only "
        "for printing (two decimals, tonnes as integers). E\\_SE per claimant. "
        f"Wet year (AW = {AWw:g}): every lens gives Q = {trio(wet['Q'])}, {f2(wet['surplus'])} Mm³ to the "
        f"aquifer, A = 1, ΣY = {t0(wet['SY'])} t, E\\_PJ = {f2(wet['E_PJ'])}, E\\_SE = {f2(wet['E_SE'])}, "
        f"F = {f2(wet['F'])}, S = {f2(wet['S'])}."
    )
    w("")

    def rows_for(card):
        return [(key, name, static_case(bv, sv, card, key, label=f"bp {card} {key}")) for key, name in LENSES]

    # ---- 3.1 dry
    dry = rows_for("dry")
    w(f"### 3.1 Dry year, AW = {bv.inflow['dry'] - bv.reserve:g}")
    w("")
    w("| Lens | Q A / B / C | A A / B / C | Y A / B / C (t) | ΣY | E\\_PJ | E\\_SE | F | UWF / PWF₃ / EWF / CWF / SWF |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for _key, name, r in dry:
        w(
            f"| {name} | {trio(r['Q'])} | {trio(r['A'])} | {trio(r['Y'], t0)} | {t0(r['SY'])} | "
            f"{f2(r['E_PJ'])} | {f2(r['E_SE'])} | {f2(r['F'])} | {f2(r['UWF'])} / {pwf_fmt(r['PWF'])} / "
            f"{f2(r['EWF'])} / {f2(r['CWF'])} / {swf_fmt(r['SWF'])} |"
        )
    w("")

    # ---- 3.2 normal, merging identical allocations only
    normal = rows_for("normal")
    w(f"### 3.2 Normal year, AW = {bv.inflow['normal'] - bv.reserve:g}")
    w("")
    w("| Lens | Q A / B / C | A A / B / C | Y A / B / C (t) | ΣY | E\\_PJ | E\\_SE | F |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- |")
    used, merges = set(), {}
    for i, (key, name, r) in enumerate(normal):
        if key in used:
            continue
        same = [(k2, n2) for k2, n2, r2 in normal[i + 1 :] if np.allclose(r["Q"], r2["Q"], atol=1e-9)]
        used.update(k for k, _ in same)
        label = name
        if same:
            label = f"{name} (= {' = '.join(n for _, n in same)} here)"
            merges[key] = [k for k, _ in same]
        w(
            f"| {label} | {trio(r['Q'])} | {trio(r['A'])} | {trio(r['Y'], t0)} | {t0(r['SY'])} | "
            f"{f2(r['E_PJ'])} | {f2(r['E_SE'])} | {f2(r['F'])} |"
        )
    w("")
    dry_co = [
        (k1, k2) for i, (k1, _, a) in enumerate(dry) for (k2, _, b) in dry[i + 1 :] if np.allclose(a["Q"], b["Q"], atol=1e-9)
    ]
    assert {round(r["S"], 9) for _, _, r in dry + normal} == {1.0}
    co_txt = []
    for k, others in merges.items():
        for o in others:
            why = ""
            if {k, o} == {"equal_sacrifice", "talmud"}:
                AWn = bv.inflow["normal"] - bv.reserve
                Dn = np.array([x.D for x in sv])
                loss = (Dn.sum() - AWn) / len(Dn)
                assert AWn >= Dn.sum() / 2 and loss <= (Dn / 2).min()
                why = (
                    f" (AW ≥ ½ΣD and the equal loss {f2(loss)} exceeds no half-claim, the smallest being "
                    f"{f2((Dn / 2).min())})"
                )
            co_txt.append(f"{lname(names[k])} equals {lname(names[o])}{why}")
    nU = normal[0][2]
    lost = [
        lname(names[k])
        for k in ("weighted_utilitarian", "sufficientarian")
        if not np.allclose(next(r for kk, _, r in normal if kk == k)["Q"], nU["Q"])
    ]
    sent = "S = 1.00 and r₃ = 1 in every row of both tables under the v1 reduction. "
    if co_txt:
        sent += (
            ("One normal-year coincidence is a fixture: " if len(co_txt) == 1 else "Normal-year coincidences are fixtures: ")
            + "; ".join(co_txt)
            + ". "
        )
    else:
        sent += "No two lenses coincide in the normal year. "
    if not dry_co:
        sent += "No two lenses coincide in the dry year. "
    if lost:
        sent += (
            f"With crop values the utilitarian maximiser no longer coincides with the {' or the '.join(lost)} "
            f"lens: in the normal year it fills the citrus estate, gives the paddy the rest and leaves the "
            f"wheat farms {f2(nU['Q'][2])} Mm³."
        )
    w(sent.strip())
    w("")

    # ---- 3.3 dynamic fixtures (full scenario)
    w("### 3.3 Dynamic fixtures")
    w("")
    w("Full Kelvara scenario; proportional lens unless stated; one season is one year.")
    w("")
    w("| Fixture | Setup | Expected |")
    w("| --- | --- | --- |")
    (pm,), _ = run_game(bf, sf, ["normal"], pump="full", case="bp pumping", quiet=True)
    assert np.allclose(pm["A"], pm["A"][0])
    w(
        f"| Pumping | Normal, proportional, each pumps its capacity ({bf.cap_share:g} × D = {trio(pm['P'])}) | "
        f"W = {trio(pm['W'])}; A = {f2(pm['A'][0])} all; ΣY = {t0(pm['SY'])}; F = {f2(pm['F'])}; "
        f"S = {f2(pm['S'])}, r₃ = {f2(pm['r3'])}; B = {f2(pm['B_next'])}; cost per Mm³ {trio(pm['cost'])} |"
    )
    deck = ["dry", "dry", "normal", "normal", "wet", "dry"]
    sel, _ = run_game(bf, sf, deck, pump="full", case="bp selfish", quiet=True)
    iB = next(i for i, x in enumerate(sf) if x.wells_fail is not None)
    fail_rounds = [o["t"] for o in sel if o["caps"][iB] == 0.0]
    rat_rounds = [o["t"] for o in sel if o["rationed"]]
    losses = [o["loss_in"] for o in sel if o["loss_in"] > 0]
    deck_txt = ", ".join(c.capitalize() if j == 0 else c for j, c in enumerate(deck))
    w(
        f"| Selfish depletion | {deck_txt}; each pumps its capacity every season | "
        f"B = {', '.join(f2(o['B_next']) for o in sel)} after each season; the paddy wells fail in season "
        f"{fail_rounds[0]} (observed level {t0(sel[fail_rounds[0] - 1]['B_obs'])} ≤ {t0(sf[iB].wells_fail)}) "
        f"and deliver nothing in seasons {rounds_txt(fail_rounds)}; requests are rationed to the stock above "
        f"B\\_res in seasons {rounds_txt(rat_rounds)}; baseflow lost {' + '.join(f2(x) for x in losses)} = "
        f"{f2(sum(losses))} Mm³ |"
    )
    coop, _ = run_game(bf, sf, deck, case="bp cooperative", quiet=True)
    assert all(abs(o["B_next"] - bf.B0) < EPS for o in coop)
    sp = {}
    for o in coop:
        sp.setdefault(o["card"], o["spill"])
    w(
        f"| Cooperative | Same deck, no pumping | B stays {f2(bf.B0)}; spill "
        f"{', '.join(f'{f2(v)} ({k})' for k, v in sp.items())} Mm³ a season; S ≤ "
        f"{f2(max(o['S'] for o in coop))} |"
    )
    (rf,), _ = run_game(bf, sf, ["normal"], case="bp return", quiet=True)
    w(
        f"| Return flow | Normal, proportional, no pumping | Σ(1 − βᵢ)Wᵢ = "
        f"{' + '.join(f2(x) for x in rf['ret_each'])} = {f2(rf['ret'])} Mm³; the share ρ = {bf.rho:g}, "
        f"{f2(rf['recharge_ret'])}, recharges the aquifer and {f2(rf['river_ret'])} returns to the river below "
        f"the off-takes; with r₀ = {bf.r0:g} the full aquifer spills {f2(rf['spill'])} |"
    )
    bl = (18, 15, 12, 10)
    w(
        f"| Baseflow | B after the season = {', '.join(map(str, bl))} | next inflow reduced by "
        f"{', '.join(f2(baseflow_loss(bf, b)) for b in bl)} Mm³ |"
    )
    orc, _ = run_game(bf, sf, ["normal"] * 3, actions={1: {"B": "orchard"}}, case="bp orchard", quiet=True)
    i = ids.index("B")
    assert orc[1]["act_cost"][i] == ORCHARD_COST and orc[0]["D"][i] == orc[1]["D"][i]
    w(
        f"| Orchard lag | B plays Orchard in season 2 | D\\_B = {f2(orc[2]['D'][i])}, K\\_B = {t0(orc[2]['K'][i])}, "
        f"p\\_B = {f2(orc[2]['p'][i])} from season 3; L\\_B −= {ORCHARD_COST:g} in season 2 |"
    )
    de, _ = run_game(bf, sf, ["normal"] * 3, actions={0: {"C": "drip"}, 1: {"C": "expand"}}, case="bp drip", quiet=True)
    c = ids.index("C")
    w(
        f"| Drip then Expand | C: Drip season 1, Expand season 2 | D\\_C = {f2(de[1]['D'][c])}, K\\_C = "
        f"{t0(de[1]['K'][c])} from season 2; D\\_C = {f2(de[2]['D'][c])}, K\\_C = {t0(de[2]['K'][c])}, area "
        f"{t0(de[2]['area'][c])} ha from season 3; ΣD {f2(sum(de[1]['D']))} then {f2(sum(de[2]['D']))} |"
    )
    eq = static_case(bf, sf, "dry", "proportional", label="bp equalisandum")
    w(
        f"| Equalisandum | Dry, proportional; switch u | E\\_SE per claimant {f2(eq['E_SE'])}; per hectare "
        f"{f2(eq['E_SE_ha'])}; per person {f2(eq['E_SE_N'])} |"
    )
    cols = [("UWF", "UWF"), ("PWF", "PWF₃"), ("EWF", "EWF"), ("CWF", "CWF"), ("SWF", "SWF")]
    AWd = bf.inflow["dry"] - bf.reserve
    keys = [k for k, _ in LENSES]

    def ranks(idx):
        parts = []
        for c_, lab in cols:
            vals = [r[c_] for _, _, r in dry]
            v = vals[idx]
            rank = 1 + sum(1 for x in vals if x > v + 1e-12)
            ties = sum(1 for x in vals if abs(x - v) <= 1e-12)
            vs = pwf_fmt(v) if c_ == "PWF" else (swf_fmt(v) if c_ == "SWF" else f2(v))
            parts.append(
                f"{lab} {vs} ranks {rank} of {len(vals)}" + (f" (tied with {ties - 1} other lenses)" if ties > 1 else "")
            )
        return "; ".join(parts)

    for voted, label in (("proportional", "Verdict match"), ("utilitarian", "Verdict mismatch")):
        idx = keys.index(voted)
        v9, _, d9 = verdict(sf, AWd, dry[idx][2]["A"], voted, keys)
        extra = ""
        if voted == "utilitarian":
            jb = int(np.argmax([r["UWF"] for _, _, r in dry]))
            extra = f"; the highest UWF is {lname(dry[jb][1])}'s {f2(dry[jb][2]['UWF'])}"
        lead = (
            "the verdict matches the vote"
            if voted == "proportional"
            else "the verdict matches the vote, the welfare columns do not"
        )
        w(
            f"| {label} | Dry, {voted} voted, no pumping | verdict = {lname(names[v9])} "
            f"(Σ\\|A − A\\*\\| = {f2(d9)}): {lead}; pumping gap 0; ranks over the nine lenses: "
            f"{ranks(idx)}{extra} |"
        )
    gaps = []
    for card in ("dry", "normal"):
        AW_ = bf.inflow[card] - bf.reserve
        gaps.append(
            (
                np.abs(allocate("prioritarian", sf, AW_, 1.001) - allocate("egalitarian", sf, AW_)).max(),
                np.abs(allocate("prioritarian", sf, AW_, 1000.0) - allocate("proportional", sf, AW_)).max(),
            )
        )
    g_lo, g_hi = max(g[0] for g in gaps), max(g[1] for g in gaps)
    assert g_lo < 0.01 and g_hi < 0.01
    w(
        f"| Prioritarian limits | γ = 1.001 and 1,000 | within 0.01 of strict egalitarian and proportional "
        f"(largest gaps {g_lo:.4f} and {g_hi:.4f} Mm³ over the dry and normal years) |"
    )
    w("| Crop failure | C at A ≤ 0.5 in seasons 2 and 3 | flag set; score still computed |")
    w(
        "| Game length | 100 nonces | T ∈ {5, 6}, each 0.50 ± 0.05; deck 1 W / 3 N / 2 D always yields a dry "
        "season; commitment verifies for every nonce |"
    )
    deckc = [cc for cc in ("wet", "normal", "dry") for _ in range(bf.deck[cc])]
    o6 = sorted(set(itertools.permutations(deckc)))
    o5 = sorted({o[:5] for o in o6})
    summ, all_txt = [], []
    for key, name in LENSES:
        g = PRIO_GAMMA_DEFAULT if key == "prioritarian" else PRIO_GAMMA_FIXTURE
        r6, a6 = goal_rates(key, g, o6, bf, sf)
        r5, a5 = goal_rates(key, g, o5, bf, sf)
        got = []
        for j, sid in enumerate(ids):
            if r6[j] == 1 and r5[j] == 1:
                got.append(sid)
            elif r6[j] > 0 or r5[j] > 0:
                got.append(f"{sid} in {pct(r6[j])} / {pct(r5[j])}")
        lab = name.replace(" (γ = 3 fixture)", f" (γ = {PRIO_GAMMA_DEFAULT:g})")
        lab = lname(lab)
        summ.append(f"{lab} {', '.join(got) if got else 'none'}")
        if a6 > 0 or a5 > 0:
            all_txt.append(f"{lab} ({pct(a6)} of decks at T = 6, {pct(a5)} at T = 5)")
    full, _ = run_game(bf, sf, deckc, case="bp goals full", quiet=True)
    shareA = sum(o["dL"][0] for o in full) / sum(o["potential"][0] for o in full)
    w(
        f"| Goal attainability | All-principled, no pumping; every order of 1W/3N/2D (T = 6, {len(o6)} decks) "
        f"and every five-card sequence (T = 5, {len(o5)}) | goals met in every deck of both lengths unless a share "
        f"(T = 6 / T = 5) is given: {'; '.join(summ)}. All three goals together only under "
        f"{', '.join(all_txt) if all_txt else 'no lens'}; under proportional with the full deck A reaches "
        f"{f1(100 * shareA)} % of potential (R15 goal {pct(sf[0].goal['threshold'])}) |"
    )
    w(
        "| Time-box | `game.timeboxed` after season 3 of a T = 5 game | game ends after season 3; T and deck still "
        "unseal; hash verifies; `truncated: true` |"
    )
    w(
        "| Timer expiry | S4 closes with no proposal in season 3 | previous season's lens applied; `lens.chosen` "
        "carries `byTimeout: true` |"
    )
    w("| Replay determinism | any record | replay on JavaScriptCore and V8 yields byte-identical `seasons.csv` |")
    w(
        "| Privacy | Normal, any lens, A pumps 2 | no public projection, export before debrief or relay message "
        "contains W\\_A, A\\_A, Y\\_A, ΔL\\_A or P\\_A; total pumping = 2 |"
    )
    w("")

    # ---- 3.4 cross-checks
    w("### 3.4 Cross-checks")
    w("")
    eg = dry[keys.index("egalitarian")][2]
    pr = dry[keys.index("proportional")][2]
    if abs(eg["E_SE"] - 1) < 1e-9 and abs(pr["E_PJ"] - 1) < 1e-9:
        w(
            f"- Dry year: strict egalitarian scores E\\_SE = {f2(eg['E_SE'])}, proportional E\\_PJ = "
            f"{f2(pr['E_PJ'])} by construction — each metric awards a perfect score to the lens that embodies it "
            f"(metric-is-a-lens)."
        )
    cap = dry[keys.index("capability")][2]
    seN = {name: r["E_SE_N"] for _, name, r in dry}
    best_N = max(seN, key=seN.get)
    w(
        f"- Capability with κ = 1 in the dry year: E\\_PJ = {f2(cap['E_PJ'])}, per-person E\\_SE = "
        f"{f2(cap['E_SE_N'])}"
        + (
            " — the highest of any lens: the equalisandum point."
            if best_N.startswith("Capability")
            else f"; the highest per-person E\\_SE is {lname(best_N)}'s {f2(seN[best_N])}."
        )
    )
    ut = dry[0][2]
    low = int(np.argmin(ut["A"]))
    if ut["A"][low] < SURVIVAL:
        w(
            f"- Strict utilitarian dry year ({sf[low].id} at {pct(ut['A'][low])} of demand, PWF₃ "
            f"{pwf_fmt(ut['PWF'])}, SWF 0) is Rawls's separateness-of-persons objection in numbers."
        )
    mv = [marginal_values(s) for s in sf]
    w(
        "- Marginal value per Mm³ of deficit water, in points: p·K·Kᵧ/D/100 above the survival kink and "
        "p·Y(0.5)/(0.5D)/100 below it — "
        + "; ".join(f"{s.id} {f2(a / 100)} above, {f2(b / 100)} below" for s, (b, a) in zip(sf, mv, strict=False))
        + "."
    )
    Bs = (20, 15, 12, 10)
    w(
        f"- Pump cost per Mm³ at an observed level B = {', '.join(map(str, Bs))}: "
        + "; ".join(f"{s.id} " + ", ".join(f2(pump_cost(bf, s, B)) for B in Bs) for s in sf)
        + f" (pump-set factors {', '.join(f'{s.pump_factor:g}' for s in sf)}; seat multipliers 1)."
    )
    allpay = all(min(a, b) / 100 > pump_cost(bf, s, bf.Bres) for s, (b, a) in zip(sf, mv, strict=False))
    fails = [s for s in sf if s.wells_fail is not None]
    keep = [s.id for s in sf if s.wells_fail is None]
    w(
        (
            "- Every scheme's marginal value exceeds its pump cost at every level down to B\\_res, so a deficit cube "
            "pays wherever a scheme has working wells. "
            if allpay
            else "- "
        )
        + "; ".join(
            f"{s.id}'s shallow wells fail once the observed level is at or below {s.wells_fail:g} "
            f"(B\\_low), so {s.id} stops pumping there"
            for s in fails
        )
        + f"; {' and '.join(keep)} keep pumping to B\\_res. The cost of depletion falls on everyone as lost "
        f"baseflow (up to {f2(baseflow_loss(bf, bf.Bres))} Mm³ a season at B\\_res) and on the paddy as failed "
        f"wells, not as a rising price of pumping."
    )
    print("### BLUEPRINT §3 TEXT\n")
    print("```markdown")
    print("\n".join(L))
    print("```")


def main():
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    basin, _ = load_scenario("full")
    print("## Reference model output (independent of the engine)\n")
    print(
        f"Scenario: {SCENARIO_PATH.relative_to(ROOT).as_posix()}; registry: "
        f"{REGISTRY_PATH.relative_to(ROOT).as_posix()}. v1 = β 1, r₀ 0, no capacity, no pumping, no "
        f"actions; full = scenario β, r₀ {basin.r0:g}, ρ {basin.rho:g}, capacity {basin.Bmax:g}, "
        f"B_low {basin.Blow:g}, B_res {basin.Bres:g}, pump capShare {basin.cap_share:g}, cost "
        f"factor × ({basin.cost_base:g} + {basin.cost_slope:g}·max(0, 1 − B/B₀)), baseflow κ "
        f"{basin.kappa_loss:g}, tank resolution {TANK_RES:g}. Prioritarian rows use γ = "
        f"{PRIO_GAMMA_FIXTURE:g} (§3) unless labelled; PWF uses γ = {WELFARE_GAMMA:g}. Drip "
        f"consumption factor {DRIP_CONSUMPTION:g}, β after {DRIP_BETA:g}.\n"
    )
    print_wet()
    dry = print_static("dry", True)
    print_static("normal", False)
    print("### §3.3 Dynamic fixtures (full scenario)\n")
    fixture_pumping()
    fixture_depletion()
    fixture_cooperative()
    fixture_return_flow()
    fixture_baseflow()
    fixture_orchard()
    fixture_drip_expand()
    fixture_equalisandum()
    fixture_verdict(dry)
    fixture_prioritarian_limits()
    fixture_goals()
    cross_checks()
    self_check()
    blueprint_text()


if __name__ == "__main__":
    main()
