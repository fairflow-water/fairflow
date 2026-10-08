// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT

import { allocate, type LensParams } from './allocate.js';
import { at, type LensId, type Scheme } from './types.js';

export interface Verdict { voted: LensId; satisfied: LensId; distance: number; pumpingGap: number }

/**
 * Blueprint §2.7 — the lens whose ideal allocation for this season is nearest the realised one, by Σ|A_i − A_i*|.
 * `lenses` are the scenario's enabled lenses in card order, with the parameters actually applied (the voted floor rule).
 * Ties go to the voted lens, then to the earlier card: two lenses can prescribe the same allocation (review E1).
 * "You voted X; the outcome best satisfied Y; the gap came from Z Mm³ of pumping."
 */
export function verdict(
  schemes: Scheme[], allocable: number, W: number[], voted: LensId, pumpingGap: number,
  lenses: { id: LensId; params: LensParams }[], survivalFloor: number,
): Verdict {
  const A = W.map((w, i) => w / at(schemes, i).demandMm3);
  const distances = lenses.map(l => {
    const ideal = allocate(l.id, schemes, allocable, l.params, survivalFloor).Q;
    return { id: l.id, d: ideal.reduce((t, q, i) => t + Math.abs(at(A, i) - q / at(schemes, i).demandMm3), 0) };
  });
  if (distances.length === 0) throw new Error('verdict: no lenses to compare');
  const nearest = Math.min(...distances.map(x => x.d));
  const tied = distances.filter(x => x.d <= nearest + 1e-9); // tolerance: 1e-9 on a sum of rounded shares (§7.2)
  const pick = tied.find(x => x.id === voted) ?? at(tied, 0);
  return { voted, satisfied: pick.id, distance: pick.d, pumpingGap };
}
