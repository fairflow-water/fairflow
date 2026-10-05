// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
//
// Mirror of packages/engine-py/src/fairflow_engine/production.py (ADR 0002).

import type { Scheme } from './types.js';

/**
 * Blueprint §2.4 — FAO-33 seasonal yield response (Doorenbos & Kassam 1979), in t.
 * Y = K(1 − K_y(1 − min(A, 1))) for A ≥ floor, else Y(floor)·A/floor, with A = W/D. The survival floor is a
 * parameter (registry `indicators.survivalFloor`), never a constant here.
 */
export function yieldOf(s: Scheme, waterMm3: number, survivalFloor: number): number {
  const A = Math.max(0, waterMm3) / s.demandMm3;
  const fao33 = (a: number) => s.capacityT * (1 - s.ky * (1 - Math.min(a, 1)));
  return A >= survivalFloor ? fao33(A) : (fao33(survivalFloor) * A) / survivalFloor;
}

/** Value of a scheme's harvest, p·Y. */
export const valueOf = (s: Scheme, waterMm3: number, survivalFloor: number): number => s.price * yieldOf(s, waterMm3, survivalFloor);
