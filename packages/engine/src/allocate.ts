// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import { SURVIVAL_ADEQUACY, valueOf } from './production.js';
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

/**
 * Lens parameters (scenario `lenses[]`, blueprint §6.1).
 * Prioritarian: Q_i ∝ w_i^(1/γ) · D_i^(1−1/γ), default γ = 2, w = 1.
 * Sufficientarian: floor × D_i for all, scaled proportionally or by CEA when short; remainder by `secondary` (default max_value).
 */
export interface LensParams {
  gamma?: number; weight?: '1' | 'people';
  floor?: number; floorScaling?: 'proportional' | 'cea'; secondary?: 'max_value' | 'prioritarian' | 'proportional';
}

/**
 * Blueprint §2.3 utilitarian — maximise Σ p_i Y_i subject to lo_i ≤ Q_i ≤ hi_i and Σ Q_i = min(AW, Σ hi_i).
 * Production is piecewise linear in Q with breakpoints at ½D and D, and not concave (the survival branch), so a greedy
 * fill can stop at a local optimum. Exact instead: with each Q_i's segment fixed the problem is an LP with one coupling
 * constraint, so some optimum has at most one Q_i strictly inside a segment. Enumerate that scheme and the breakpoints
 * of the others: n · 3^(n−1) candidates, 405 for five schemes. Ties keep the first candidate, so the result is deterministic.
 */
export function maxValue(schemes: Scheme[], allocable: number, lo: number[] = schemes.map(() => 0)): number[] {
  const n = schemes.length;
  const hi = schemes.map(s => s.demandMm3);
  const budget = Math.min(allocable, hi.reduce((a, b) => a + b, 0));
  const points = schemes.map((s, i) => [...new Set([lo[i], SURVIVAL_ADEQUACY * s.demandMm3, hi[i]])].filter(x => x >= lo[i] && x <= hi[i]));
  let best: number[] | null = null; let bestValue = 0;
  for (let k = 0; k < n; k++) {
    const others = [...Array(n).keys()].filter(i => i !== k);
    const visit = (j: number, x: number[]): void => {
      if (j < others.length) { for (const p of points[others[j]]) { x[others[j]] = p; visit(j + 1, x); } return; }
      const rest = budget - others.reduce((t, i) => t + x[i], 0);
      if (rest < lo[k] - 1e-9 || rest > hi[k] + 1e-9) return;
      x[k] = Math.min(hi[k], Math.max(lo[k], rest));
      const v = schemes.reduce((t, s, i) => t + valueOf(s, x[i]), 0);
      if (best === null || v > bestValue + 1e-9 * Math.max(1, Math.abs(bestValue))) { bestValue = v; best = x.slice(); }
    };
    visit(0, new Array<number>(n).fill(0));
  }
  if (best === null) throw new Error('maxValue: no feasible allocation (floors exceed the allocable water)');
  return (best as number[]).map(round6);
}

/** Blueprint §2.3 sufficientarian — survival floor first, then the remainder by a secondary rule. */
export function sufficientarian(schemes: Scheme[], allocable: number, params: LensParams = {}): number[] {
  const D = schemes.map(s => s.demandMm3);
  const floors = D.map(d => (params.floor ?? SURVIVAL_ADEQUACY) * d);
  const sumFloors = floors.reduce((a, b) => a + b, 0);
  if (sumFloors >= allocable) {
    return params.floorScaling === 'cea'
      ? weightedCEA(floors, floors.map(() => 1), allocable)
      : floors.map(f => round6((f / sumFloors) * allocable));
  }
  const secondary = params.secondary ?? 'max_value';
  if (secondary === 'max_value') return maxValue(schemes, allocable, floors);
  const residual = D.map((d, i) => d - floors[i]);
  const weights = secondary === 'prioritarian' ? weightsFor('prioritarian', schemes, params) : residual;
  const extra = weightedCEA(residual, weights, allocable - sumFloors);
  return floors.map((f, i) => round6(f + extra[i]));
}

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

/** Entry point: every lens of blueprint §2.3 except user-defined criteria (the §6.1 grammar). */
export function allocate(lens: LensId, schemes: Scheme[], allocable: number, params: LensParams = {}): Allocation {
  const D = schemes.map(x => x.demandMm3);
  let Q: number[];
  if (lens === 'equal_sacrifice') Q = cel(D, allocable);
  else if (lens === 'talmud') Q = talmud(D, allocable);
  else if (lens === 'utilitarian') Q = maxValue(schemes, allocable);
  else if (lens === 'sufficientarian') Q = sufficientarian(schemes, allocable, params);
  else Q = weightedCEA(D, weightsFor(lens, schemes, params), allocable);
  const surplus = round6(Math.max(0, allocable - Q.reduce((a, b) => a + b, 0)));
  return { lens, Q, surplusToAquifer: surplus };
}
