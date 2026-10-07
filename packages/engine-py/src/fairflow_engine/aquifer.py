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


def pump_cost_per_mm3(basin: Basin, stock: float, seat: int) -> float:
    """c = costBase + costSlope·max(0, 1 − B/B₀) per Mm³, × the seat multiplier once B < B_low (§2.2), with B the
    observed level (ADR 0004). ADR 0006: the cost never falls below costBase, the cost at B₀, the shallowest level the
    blueprint calibrates; above it the formula would turn negative and pay farms to pump. Seats beyond the multiplier
    list use its last value."""
    q, p = basin.aquifer, basin.pump
    seen = observed_stock(basin, stock)
    base = p.costBase + p.costSlope * max(0.0, 1 - seen / q.initial)
    if seen >= q.lowThreshold:
        return base
    m = q.seatCostMultipliers
    return base * m[min(seat, len(m)) - 1]


def ration_pumps(basin: Basin, stock: float, requests: Sequence[float]) -> list[float]:
    """Pumping draws only above B_res; requests beyond the available stock are rationed pro rata (§2.6)."""
    for r in requests:
        if r < 0 or r > basin.pump.cap:
            raise ValueError(f"pump request {r} outside 0..{basin.pump.cap}")
    available = max(0.0, stock - basin.aquifer.reserve)
    asked = sum(requests)
    return list(requests) if asked <= available else [r * available / asked for r in requests]


def return_flow(schemes: Sequence[Scheme], W: Sequence[float]) -> float:
    """Σ (1 − β_i) W_i (§2.6)."""
    return sum((1 - s.beta) * w for s, w in zip(schemes, W, strict=True))


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
    """Next inflow falls by maxLoss·(B_low − B)/B_low while B < B_low (§2.2, §2.6), B the observed level (ADR 0004)."""
    low, loss = basin.aquifer.lowThreshold, basin.aquifer.maxInflowLossMm3
    return loss * max(0.0, (low - observed_stock(basin, stock_next)) / low)
