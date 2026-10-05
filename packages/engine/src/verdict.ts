// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import { allocate, type LensParams } from './allocate.js';
import { at, type LensId, type Scheme } from './types.js';

export interface Verdict { voted: LensId; satisfied: LensId; distance: number; pumpingGap: number }

/**
 * Blueprint §2.7 — the lens whose ideal allocation for this season is nearest the realised one, by Σ|A_i − A_i*|.
 * `lenses` are the scenario's enabled lenses in card order; ties go to the earlier card, so the verdict maps onto a card.
 * "You voted X; the outcome best satisfied Y; the gap came from Z Mm³ of pumping."
 */
export function verdict(
  schemes: Scheme[], allocable: number, W: number[], voted: LensId, pumpingGap: number,
  lenses: { id: LensId; params: LensParams }[], survivalFloor: number,
): Verdict {
  const A = W.map((w, i) => w / at(schemes, i).demandMm3);
  let best: Verdict | null = null;
  for (const l of lenses) {
    const ideal = allocate(l.id, schemes, allocable, l.params, survivalFloor).Q;
    const distance = ideal.reduce((t, q, i) => t + Math.abs(at(A, i) - q / at(schemes, i).demandMm3), 0);
    if (best === null || distance < best.distance - 1e-9) best = { voted, satisfied: l.id, distance, pumpingGap }; // tolerance for ties (§2.7)
  }
  if (best === null) throw new Error('verdict: no lenses to compare');
  return best;
}
