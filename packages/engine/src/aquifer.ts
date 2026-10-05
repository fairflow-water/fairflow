// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
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
 * c = costBase + costSlope·(1 − B/B₀), times the seat multiplier once B < B_low.
 */
export function pumpCostPerMm3(basin: Basin, stock: number, seat: number): number {
  const { aquifer: q, pump } = basin;
  const seen = observedStock(basin, stock);
  const base = pump.costBase + pump.costSlope * (1 - seen / q.initial);
  if (seen >= q.lowThreshold) return base;
  const m = q.seatCostMultipliers;
  return base * at(m, Math.min(seat, m.length) - 1);
}

/** Pumping draws only above B_res; requests beyond the available stock are rationed pro rata (§2.6). */
export function rationPumps(basin: Basin, stock: number, requests: number[]): number[] {
  for (const r of requests) if (r < 0 || r > basin.pump.cap) throw new RangeError(`pump request ${r} outside 0..${basin.pump.cap}`);
  const available = Math.max(0, stock - basin.aquifer.reserve);
  const asked = requests.reduce((a, b) => a + b, 0);
  return asked <= available ? requests.slice() : requests.map(r => (r * available) / asked);
}

/** Return flows Σ(1 − β_i) W_i recharge the aquifer (§2.6). */
export const returnFlow = (schemes: Scheme[], W: number[]): number => W.reduce((t, w, i) => t + (1 - at(schemes, i).beta) * w, 0);

/** §2.6 — B_{t+1} = max(B_res, B_t + surplus + r₀ + return flows − Σ P). */
export function nextStock(basin: Basin, stock: number, surplus: number, returns: number, pumped: number): number {
  return Math.max(basin.aquifer.reserve, stock + surplus + basin.aquifer.naturalRecharge + returns - pumped);
}

/** §2.6 GW–SW coupling — next inflow falls by maxLoss·(B_low − B)/B_low while B < B_low, B the observed level (ADR 0004). */
export function inflowLossNext(basin: Basin, stockNext: number): number {
  const { lowThreshold: low, maxInflowLossMm3: loss } = basin.aquifer;
  return loss * Math.max(0, (low - observedStock(basin, stockNext)) / low);
}
