// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import type { Scheme } from './types.js';

/** Adequacy below which the FAO-33 relation is replaced by a linear fall to zero (blueprint §2.4). */
export const SURVIVAL_ADEQUACY = 0.5;

/**
 * Blueprint §2.4 — FAO-33 seasonal yield response (Doorenbos & Kassam 1979), in t.
 * A = W/D; Y = K(1 − K_y(1 − min(A, 1))) for A ≥ 0.5, else Y(0.5)·A/0.5. Water above demand adds nothing.
 */
export function yieldOf(s: Scheme, waterMm3: number): number {
  const A = Math.max(0, waterMm3) / s.demandMm3;
  const full = (a: number) => s.capacityT * (1 - s.ky * (1 - Math.min(a, 1)));
  return A >= SURVIVAL_ADEQUACY ? full(A) : (full(SURVIVAL_ADEQUACY) * A) / SURVIVAL_ADEQUACY;
}

/** Value of a scheme's harvest, p·Y. */
export const valueOf = (s: Scheme, waterMm3: number): number => s.price * yieldOf(s, waterMm3);
