# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §2.2 and §2.6 — pumping, rationing, return flows, recharge and GW–SW coupling."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .model import Basin, Scheme, round6


def observed_stock(basin: Basin, stock: float) -> float:
    """ADR 0004: the level players see — the last full step of `tankResolution` below the true stock."""
    res = basin.aquifer.tankResolution
    return math.floor(round6(stock / res)) * res


def pump_cost_per_mm3(basin: Basin, stock: float, seat: int, factor: float = 1.0) -> float:
    """c = factor·(costBase + costSlope·max(0, 1 − B/B₀)) per Mm³, × the seat multiplier once B < B_low (§2.2), with B
    the observed level (ADR 0004). ADR 0006: never below costBase·factor. ADR 0008: the cost is lift energy, linear in
    the head (E = ρgH/η), so costSlope/costBase = B₀ / (storage per metre × head at B₀); `factor` is the scheme's
    pumpCostFactor, η_ref/η_i, applied always. Seats beyond the multiplier list use its last value."""
    q, p = basin.aquifer, basin.pump
    seen = observed_stock(basin, stock)
    base = factor * (p.costBase + p.costSlope * max(0.0, 1 - seen / q.initial))
    if seen >= q.lowThreshold:
        return base
    m = q.seatCostMultipliers
    return base * m[min(seat, len(m)) - 1]


def pump_cap(basin: Basin, stock: float, scheme: Scheme) -> float:
    """The most a scheme can pump this season: capShare × its demand (ADR 0008: wells in proportion to irrigated area,
    so Expand adds wells), or the flat cap; 0 once the observed stock is at or below the level where its shallow wells
    fail (the suction limit; Sekhri 2014; Jasechko & Perrone 2021)."""
    if scheme.wellsFailAtOrBelow is not None and observed_stock(basin, stock) <= scheme.wellsFailAtOrBelow:
        return 0.0
    share = basin.pump.capShare
    return basin.pump.cap if share is None else round6(share * scheme.demandMm3)


def ration_pumps(basin: Basin, stock: float, requests: Sequence[float], caps: Sequence[float] | None = None) -> list[float]:
    """Pumping draws only above B_res; requests beyond the available stock are rationed pro rata (§2.6). `caps` are the
    schemes' pump caps this season (pump_cap); without them the flat cap applies."""
    limits = list(caps) if caps is not None else [basin.pump.cap] * len(requests)
    for r, limit in zip(requests, limits, strict=True):
        if r < 0 or r > limit + 1e-9:  # tolerance: caps are rounded to 1e-6 Mm³ (§7.2)
            raise ValueError(f"pump request {r} outside 0..{limit}")
    available = max(0.0, stock - basin.aquifer.reserve)
    asked = sum(requests)
    return list(requests) if asked <= available else [r * available / asked for r in requests]


def return_flow(schemes: Sequence[Scheme], W: Sequence[float], recharge_share: float = 1.0) -> float:
    """ρ Σ (1 − β_i) W_i (§2.6): the non-consumed water that reaches the shared aquifer. The rest, (1 − ρ) of it, returns
    through drains and baseflow to the river below the schemes' off-takes, so it leaves the basin's shared stores
    (ADR 0007; Karimi et al. 2013 for the split)."""
    return recharge_share * sum((1 - s.beta) * w for s, w in zip(schemes, W, strict=True))


def _unbounded_stock(basin: Basin, stock: float, surplus: float, returns: float, pumped: float) -> float:
    """max(B_res, B_t + surplus + r₀ + Σ(1 − β_i)W_i − ΣP_i): §2.6 before the capacity of ADR 0006."""
    return max(basin.aquifer.reserve, stock + surplus + basin.aquifer.naturalRecharge + returns - pumped)


def next_stock(basin: Basin, stock: float, surplus: float, returns: float, pumped: float) -> float:
    """B_{t+1} = min(B_max, max(B_res, B_t + surplus + r₀ + Σ(1 − β_i)W_i − ΣP_i)) (§2.6, ADR 0006 B_max)."""
    unbounded = _unbounded_stock(basin, stock, surplus, returns, pumped)
    cap = basin.aquifer.capacity
    return unbounded if cap is None else min(cap, unbounded)


def aquifer_spill(basin: Basin, stock: float, surplus: float, returns: float, pumped: float) -> float:
    """ADR 0006: recharge a full aquifer rejects (Theis 1940). It leaves as the natural discharge the climate cards'
    inflows already contain, so it is recorded for the debrief and never added to the river (no double counting)."""
    return _unbounded_stock(basin, stock, surplus, returns, pumped) - next_stock(basin, stock, surplus, returns, pumped)


def aquifer_full(basin: Basin, stock: float) -> bool:
    """Whether the observed level has reached the observed capacity: what the table may know (ADR 0004, ADR 0006)."""
    cap = basin.aquifer.capacity
    return cap is not None and observed_stock(basin, stock) >= observed_stock(basin, cap)


def inflow_loss_next(basin: Basin, stock_next: float) -> float:
    """Baseflow lost from next season's inflow, B the observed level (ADR 0004). ADR 0008: κ·(B₀ − B) from the first
    drawdown below B₀ — pumping captures streamflow (Konikow & Leake 2014; Barlow & Leake 2012). Without κ, the §2.2
    rule: maxLoss·(B_low − B)/B_low while B < B_low."""
    q = basin.aquifer
    seen = observed_stock(basin, stock_next)
    if q.baseflowLossPerMm3 is not None:
        return q.baseflowLossPerMm3 * max(0.0, q.initial - seen)
    return q.maxInflowLossMm3 * max(0.0, (q.lowThreshold - seen) / q.lowThreshold)
