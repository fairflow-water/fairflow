// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT

// Mirror of packages/engine-py/src/fairflow_engine/aquifer.py (ADR 0002).

import { at, round6, type Basin, type Scheme } from './types.js';

/** ADR 0004: the level players see — the last full step of `tankResolution` below the true stock. */
export function observedStock(basin: Basin, stock: number): number {
  const res = basin.aquifer.tankResolution;
  return Math.floor(round6(stock / res)) * res;
}

/**
 * Blueprint §2.2 — pump cost per Mm³ from the observed level at the start of the season (ADR 0004):
 * c = factor·(costBase + costSlope·max(0, 1 − B/B₀)), times the seat multiplier once B < B_low. ADR 0006: never below
 * costBase·factor. ADR 0008: lift energy, linear in the head; `factor` is the scheme's pumpCostFactor (η_ref/η_i).
 */
export function pumpCostPerMm3(basin: Basin, stock: number, seat: number, factor = 1): number {
  const { aquifer: q, pump } = basin;
  const seen = observedStock(basin, stock);
  const base = factor * (pump.costBase + pump.costSlope * Math.max(0, 1 - seen / q.initial));
  if (seen >= q.lowThreshold) return base;
  const m = q.seatCostMultipliers;
  return base * at(m, Math.min(seat, m.length) - 1);
}

/** ADR 0008 — the most a scheme can pump: capShare × its demand (or the flat cap); 0 once its shallow wells fail. */
export function pumpCap(basin: Basin, stock: number, scheme: Scheme): number {
  if (scheme.wellsFailAtOrBelow !== null && observedStock(basin, stock) <= scheme.wellsFailAtOrBelow) return 0;
  return basin.pump.capShare === null ? basin.pump.cap : round6(basin.pump.capShare * scheme.demandMm3);
}

const CAP_TOLERANCE = 1e-9; // tolerance: caps are rounded to 1e-6 Mm³ (§7.2)

/** Pumping draws only above B_res; requests beyond the available stock are rationed pro rata (§2.6). */
export function rationPumps(basin: Basin, stock: number, requests: number[], caps?: number[]): number[] {
  requests.forEach((r, i) => {
    const limit = caps === undefined ? basin.pump.cap : at(caps, i);
    if (r < 0 || r > limit + CAP_TOLERANCE) throw new RangeError(`pump request ${r} outside 0..${limit}`);
  });
  const available = Math.max(0, stock - basin.aquifer.reserve);
  const asked = requests.reduce((a, b) => a + b, 0);
  return asked <= available ? requests.slice() : requests.map(r => (r * available) / asked);
}

/** Return flows Σ(1 − β_i) W_i recharge the aquifer (§2.6). */
/** ρ Σ (1 − β_i) W_i: the non-consumed water that reaches the shared aquifer; the rest returns to the river below the off-takes (ADR 0007). */
export const returnFlow = (schemes: Scheme[], W: number[], rechargeShare = 1): number =>
  rechargeShare * W.reduce((t, w, i) => t + (1 - at(schemes, i).beta) * w, 0);

/** §2.6 before the capacity of ADR 0006: max(B_res, B_t + surplus + r₀ + return flows − Σ P). */
const unboundedStock = (basin: Basin, stock: number, surplus: number, returns: number, pumped: number): number =>
  Math.max(basin.aquifer.reserve, stock + surplus + basin.aquifer.naturalRecharge + returns - pumped);

/** §2.6 with ADR 0006 — B_{t+1} = min(B_max, max(B_res, B_t + surplus + r₀ + return flows − Σ P)). */
export function nextStock(basin: Basin, stock: number, surplus: number, returns: number, pumped: number): number {
  const unbounded = unboundedStock(basin, stock, surplus, returns, pumped);
  const cap = basin.aquifer.capacity;
  return cap === null ? unbounded : Math.min(cap, unbounded);
}

/** ADR 0006 — recharge a full aquifer rejects; it leaves the basin (already in the cards' inflows), sealed until the debrief. */
export const aquiferSpill = (basin: Basin, stock: number, surplus: number, returns: number, pumped: number): number =>
  unboundedStock(basin, stock, surplus, returns, pumped) - nextStock(basin, stock, surplus, returns, pumped);

/** ADR 0006 — whether the observed level has reached the observed capacity (no more than the table already sees). */
export function aquiferFull(basin: Basin, stock: number): boolean {
  const cap = basin.aquifer.capacity;
  return cap !== null && observedStock(basin, stock) >= observedStock(basin, cap);
}

/**
 * Baseflow lost from next season's inflow, B the observed level (ADR 0004). ADR 0008: κ·(B₀ − B) from the first drawdown
 * below B₀ (capture of streamflow); without κ, the §2.2 rule maxLoss·(B_low − B)/B_low while B < B_low.
 */
export function inflowLossNext(basin: Basin, stockNext: number): number {
  const q = basin.aquifer;
  const seen = observedStock(basin, stockNext);
  if (q.baseflowLossPerMm3 !== null) return q.baseflowLossPerMm3 * Math.max(0, q.initial - seen);
  return q.maxInflowLossMm3 * Math.max(0, (q.lowThreshold - seen) / q.lowThreshold);
}
