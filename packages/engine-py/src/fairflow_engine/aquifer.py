# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Blueprint §2.2 and §2.6 — pumping, rationing, return flows, recharge and GW–SW coupling."""

from __future__ import annotations

import math
from typing import Sequence

from .model import Basin, Scheme, round6


def observed_stock(basin: Basin, stock: float) -> float:
    """ADR 0004: the level players see — the last full step of `tankResolution` below the true stock."""
    res = basin.aquifer.tankResolution
    return math.floor(round6(stock / res)) * res


def pump_cost_per_mm3(basin: Basin, stock: float, seat: int) -> float:
    """c = costBase + costSlope·(1 − B/B₀) per Mm³, × the seat multiplier once B < B_low (§2.2), with B the observed
    level (ADR 0004). Seats beyond the multiplier list use its last value."""
    q, p = basin.aquifer, basin.pump
    seen = observed_stock(basin, stock)
    base = p.costBase + p.costSlope * (1 - seen / q.initial)
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
    return sum((1 - s.beta) * w for s, w in zip(schemes, W))


def next_stock(basin: Basin, stock: float, surplus: float, returns: float, pumped: float) -> float:
    """B_{t+1} = max(B_res, B_t + surplus + r₀ + Σ(1 − β_i)W_i − ΣP_i) (§2.6)."""
    return max(basin.aquifer.reserve, stock + surplus + basin.aquifer.naturalRecharge + returns - pumped)


def inflow_loss_next(basin: Basin, stock_next: float) -> float:
    """Next inflow falls by maxLoss·(B_low − B)/B_low while B < B_low (§2.2, §2.6), B the observed level (ADR 0004)."""
    low, loss = basin.aquifer.lowThreshold, basin.aquifer.maxInflowLossMm3
    return loss * max(0.0, (low - observed_stock(basin, stock_next)) / low)
