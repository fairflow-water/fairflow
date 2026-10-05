// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import { round6, type Allocation, type LensId, type Scheme } from './types.js';

/**
 * Blueprint §2.3 — generic claims-problem solver.
 * Q_i = min(D_i, C_i / Σ_{j∈U} C_j · AW^(k)), iterated over the uncapped set U until no cap binds.
 * Weighted constrained-equal-awards; every classical rule is a choice of weights C_i (or a floor / maximiser, below).
 */
export function weightedCEA(demand: number[], weights: number[], estate: number): number[] {
  const n = demand.length; const Q = new Array<number>(n).fill(0);
  let uncapped = demand.map((_, i) => i); let remaining = Math.min(estate, demand.reduce((a, b) => a + b, 0));
  while (uncapped.length > 0 && remaining > 1e-12) {
    const W = uncapped.reduce((s, i) => s + weights[i], 0);
    const capped: number[] = [];
    for (const i of uncapped) {
      const share = (weights[i] / W) * remaining;
      if (share >= demand[i] - Q[i]) { Q[i] = demand[i]; capped.push(i); }
    }
    if (capped.length === 0) { for (const i of uncapped) Q[i] += (weights[i] / W) * remaining; break; }
    remaining = Math.min(estate, demand.reduce((a, b) => a + b, 0)) - Q.reduce((a, b) => a + b, 0);
    uncapped = uncapped.filter(i => !capped.includes(i));
  }
  return Q.map(round6);
}

/** Constrained equal losses: Σ max(0, D_i − λ) = AW (equal sacrifice, Thomson 2003). */
export function cel(demand: number[], estate: number): number[] {
  let lo = 0, hi = Math.max(...demand);
  for (let k = 0; k < 100; k++) { const mid = (lo + hi) / 2; const tot = demand.reduce((s, d) => s + Math.max(0, d - mid), 0); if (tot > estate) lo = mid; else hi = mid; }
  return demand.map(d => round6(Math.max(0, d - hi)));
}

/** Talmud rule (Aumann & Maschler 1985): CEA on half-claims when AW ≤ ½ΣD, else D/2 + CEL on half-claims. */
export function talmud(demand: number[], estate: number): number[] {
  const half = demand.map(d => d / 2); const sumD = demand.reduce((a, b) => a + b, 0);
  if (estate <= sumD / 2) return weightedCEA(half, half.map(() => 1), estate);
  const rest = cel(half, estate - sumD / 2); return half.map((h, i) => round6(h + rest[i]));
}

/** Lens parameters (scenario `lenses[].params`, blueprint §6.1). Prioritarian: Q_i ∝ w_i^(1/γ) · D_i^(1−1/γ), default γ = 2, w = 1. */
export interface LensParams { gamma?: number; weight?: '1' | 'people' }

export function weightsFor(lens: LensId, s: Scheme[], params: LensParams = {}): number[] {
  const gamma = params.gamma ?? 2;
  switch (lens) {
    case 'egalitarian': return s.map(() => 1);
    case 'proportional': return s.map(x => x.demandMm3);
    case 'weighted_utilitarian': return s.map(x => x.capacityT / x.demandMm3);
    case 'capability': return s.map(x => x.people * x.kappa);
    case 'prioritarian': {
      if (!(gamma >= 1)) throw new Error(`prioritarian: gamma must be ≥ 1, got ${gamma}`);
      return s.map(x => Math.pow(params.weight === 'people' ? x.people : 1, 1 / gamma) * Math.pow(x.demandMm3, 1 - 1 / gamma));
    }
    default: throw new Error(`${lens} is not a weight rule`);
  }
}

/** Entry point. Utilitarian (greedy maximiser) and sufficientarian (floor + secondary) are TODO for build day 2 (§8.2). */
export function allocate(lens: LensId, schemes: Scheme[], allocable: number, params: LensParams = {}): Allocation {
  const D = schemes.map(x => x.demandMm3);
  let Q: number[];
  if (lens === 'equal_sacrifice') Q = cel(D, allocable);
  else if (lens === 'talmud') Q = talmud(D, allocable);
  else if (lens === 'utilitarian' || lens === 'sufficientarian') throw new Error(`${lens}: not implemented in the scaffold (blueprint §2.3)`);
  else Q = weightedCEA(D, weightsFor(lens, schemes, params), allocable);
  const surplus = round6(Math.max(0, allocable - Q.reduce((a, b) => a + b, 0)));
  return { lens, Q, surplusToAquifer: surplus };
}
