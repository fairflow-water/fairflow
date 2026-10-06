// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT

/** Blueprint §2.1 — per-season state. Units: Mm³, t, points. All numbers rounded to 1e-6 at the event boundary (§7.2). */
export interface Scheme {
  id: string; name: string; seat: number;
  demandMm3: number;      // D_i
  capacityT: number;      // K_i
  ky: number;             // FAO-33 K_y
  beta: number;           // consumptive fraction
  people: number; kappa: number; price: number; areaHa: number;
}
/**
 * Blueprint §2.2, §2.6 — basin parameters the season resolution needs. Every value comes from the scenario
 * (`basin.reserve`, `basin.aquifer`, `actions.pump`); the engine holds no defaults for them.
 */
export interface Basin {
  reserve: number;
  aquifer: {
    initial: number; reserve: number; lowThreshold: number; naturalRecharge: number;
    seatCostMultipliers: number[];   // by seat, applied once B < B_low; seats beyond the list use its last value
    maxInflowLossMm3: number;        // GW–SW coupling; 0 disables it
    tankResolution: number;          // ADR 0004: resolution of the observed level (prices pumping, drives coupling)
  };
  pump: { cap: number; costBase: number; costSlope: number };
}
export type LensId = 'utilitarian' | 'weighted_utilitarian' | 'egalitarian' | 'proportional' | 'capability' | 'sufficientarian' | 'prioritarian' | 'equal_sacrifice' | 'talmud';
export interface Allocation { lens: LensId; Q: number[]; surplusToAquifer: number }
/** §7.2 — every stored number rounded to 1e-6 at the event boundary, half up; same formula as the Python engine. */
export const round6 = (x: number): number => Math.floor(x * 1e6 + 0.5) / 1e6; // §7.2 rounding

/** Indexed read that cannot silently yield undefined (and NaN downstream): throws on an index outside the array. */
export function at<T>(values: readonly T[], index: number): T {
  const v = values[index];
  if (v === undefined) throw new RangeError(`index ${index} outside 0..${values.length - 1}`);
  return v;
}
