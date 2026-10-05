// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
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
export interface Basin { reserve: number; aquifer: { initial: number; reserve: number; lowThreshold: number; naturalRecharge: number } }
export type LensId = 'utilitarian' | 'weighted_utilitarian' | 'egalitarian' | 'proportional' | 'capability' | 'sufficientarian' | 'prioritarian' | 'equal_sacrifice' | 'talmud';
export interface Allocation { lens: LensId; Q: number[]; surplusToAquifer: number }
export const round6 = (x: number): number => Math.round(x * 1e6) / 1e6;
