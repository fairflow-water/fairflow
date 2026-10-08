// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Mirror of packages/engine-py/src/fairflow_engine/allocate.py (ADR 0002). The Python engine is authoritative; this
// file must reproduce fixtures/conformance.json. No parameter has a default here: missing values throw MissingParameter.

import { valueOf } from './production.js';
import { at, round6, type Allocation, type LensId, type Scheme } from './types.js';

/** A parameter the computation needs was not supplied by the scenario or the registry. */
export class MissingParameter extends Error {}

/** Numerical tolerances (not model parameters). */
const EPS_WATER = 1e-12;   // tolerance: Mm³ below which nothing is left to share
const EPS_FEASIBLE = 1e-9; // tolerance: slack when testing a candidate against its bounds
const EPS_TIE = 1e-9;      // tolerance: relative margin for "strictly better" between candidates
const BISECTION_STEPS = 100; // tolerance: halvings of the λ interval (far below 1e-6)

/**
 * Blueprint §2.3 — generic claims-problem solver.
 * Q_i = min(D_i, C_i / Σ_{j∈U} C_j · AW^(k)), iterated over the uncapped set U until no cap binds.
 */
export function weightedCEA(demand: number[], weights: number[], estate: number): number[] {
  if (demand.some((d, i) => d > 0 && at(weights, i) <= 0)) { // review E4: a zero weight leaves Σ C_j = 0 once the others are capped
    throw new Error('weightedCEA: every positive claim needs a positive weight');
  }
  const n = demand.length; const Q = new Array<number>(n).fill(0);
  let uncapped = demand.map((_, i) => i); let remaining = Math.min(estate, demand.reduce((a, b) => a + b, 0));
  while (uncapped.length > 0 && remaining > EPS_WATER) {
    const W = uncapped.reduce((s, i) => s + at(weights, i), 0);
    const capped: number[] = [];
    for (const i of uncapped) {
      const share = (at(weights, i) / W) * remaining;
      if (share >= at(demand, i) - at(Q, i)) { Q[i] = at(demand, i); capped.push(i); }
    }
    if (capped.length === 0) { for (const i of uncapped) Q[i] = at(Q, i) + (at(weights, i) / W) * remaining; break; }
    remaining = Math.min(estate, demand.reduce((a, b) => a + b, 0)) - Q.reduce((a, b) => a + b, 0);
    uncapped = uncapped.filter(i => !capped.includes(i));
  }
  return Q.map(round6);
}

/** §2.3 equal sacrifice, constrained equal losses: Σ max(0, D_i − λ) = AW (Thomson 2003). λ by bisection. */
export function cel(demand: number[], estate: number): number[] {
  if (estate >= demand.reduce((a, b) => a + b, 0)) return demand.map(round6);
  let lo = 0, hi = Math.max(...demand);
  for (let k = 0; k < BISECTION_STEPS; k++) {
    const mid = (lo + hi) / 2; const tot = demand.reduce((s, d) => s + Math.max(0, d - mid), 0); // tolerance: bisection midpoint
    if (tot > estate) lo = mid; else hi = mid;
  }
  return demand.map(d => round6(Math.max(0, d - hi)));
}

/** §2.3 Talmud (Aumann & Maschler 1985): AW ≤ ½ΣD: CEA on half-claims; else D_i/2 + CEL on half-claims. */
export function talmud(demand: number[], estate: number): number[] {
  const half = demand.map(d => d / 2); const sumHalf = half.reduce((a, b) => a + b, 0); // §2.3 Talmud half-claims
  if (estate <= sumHalf) return weightedCEA(half, half.map(() => 1), estate);
  const rest = cel(half, estate - sumHalf); return half.map((h, i) => round6(h + at(rest, i)));
}

/** Lens parameters (scenario `lenses[]`, §6.1; ADR 0003 for floorScaling). Required only by the lens that uses them. */
export interface LensParams {
  gamma?: number; weight?: '1' | 'people';
  floor?: number; floorScaling?: FloorRule; secondary?: 'max_value' | 'prioritarian' | 'proportional';
}

function need<K extends keyof LensParams>(params: LensParams, name: K, lens: LensId): NonNullable<LensParams[K]> {
  const v = params[name];
  if (v === undefined || v === null) throw new MissingParameter(`lens ${lens} needs parameter '${name}'`);
  return v;
}

/** ADR 0003 floor-shortfall options → the §2.3 lens that cuts the floors. */
export const FLOOR_RULES = {
  proportional: 'proportional', cea: 'egalitarian', cel: 'equal_sacrifice', talmud: 'talmud', capability: 'capability',
} as const satisfies Record<string, LensId>;
export type FloorRule = keyof typeof FLOOR_RULES;

const TIE_DIGITS = 9; // rounding: slopes equal to 1e-9 t per Mm³ tie, as in the Python engine

/**
 * §2.3 utilitarian — maximise Σ p_i Y_i subject to lo_i ≤ Q_i ≤ D_i and Σ Q_i = min(AW, ΣD).
 * The Python authority solves this as a MILP (scipy/HiGHS). The mirror enumerates instead: with each Q_i's segment
 * fixed the problem is an LP with one coupling constraint, so some optimum has at most one Q_i strictly inside a
 * segment; enumerate that scheme and the breakpoints (lo, survivalFloor·D, D) of the others. Conformance with the
 * Python engine is checked in CI (fixtures/conformance.json).
 */
export function maxValue(schemes: Scheme[], allocable: number, survivalFloor: number, lo: number[] = schemes.map(() => 0)): number[] {
  const n = schemes.length;
  // Review E5: equal marginal values make the optimum non-unique. The Python authority then takes the leximin optimum in
  // adequacy (a sequence of MILPs); the mirror has no MILP, so it refuses rather than return a different optimum.
  const perScheme = schemes.map(s => {
    const L = survivalFloor * s.demandMm3; const H = s.demandMm3 - L;
    const vL = valueOf(s, L, survivalFloor);
    return new Set([L > 0 ? vL / L : 0, H > 0 ? (valueOf(s, s.demandMm3, survivalFloor) - vL) / H : 0].map(v => v.toFixed(TIE_DIGITS)));
  }); // only a slope shared by two schemes makes a tie
  if (perScheme.reduce((t, x) => t + x.size, 0) > new Set(perScheme.flatMap(x => [...x])).size) {
    throw new Error('maxValue: tied marginal values; the canonical (leximin) optimum is computed by the Python engine');
  }
  const hi = schemes.map(s => s.demandMm3);
  const budget = Math.min(allocable, hi.reduce((a, b) => a + b, 0));
  const points = schemes.map((s, i) => [...new Set([at(lo, i), survivalFloor * s.demandMm3, at(hi, i)])].filter(x => x >= at(lo, i) && x <= at(hi, i)));
  let best: number[] | null = null; let bestValue = 0;
  for (let k = 0; k < n; k++) {
    const others = [...Array(n).keys()].filter(i => i !== k);
    const visit = (j: number, x: number[]): void => {
      if (j < others.length) { for (const p of at(points, at(others, j))) { x[at(others, j)] = p; visit(j + 1, x); } return; }
      const rest = budget - others.reduce((t, i) => t + at(x, i), 0);
      if (rest < at(lo, k) - EPS_FEASIBLE || rest > at(hi, k) + EPS_FEASIBLE) return;
      x[k] = Math.min(at(hi, k), Math.max(at(lo, k), rest));
      const v = schemes.reduce((t, s, i) => t + valueOf(s, at(x, i), survivalFloor), 0);
      if (best === null || v > bestValue + EPS_TIE * Math.max(1, Math.abs(bestValue))) { bestValue = v; best = x.slice(); }
    };
    visit(0, new Array<number>(n).fill(0));
  }
  if (best === null) throw new Error('maxValue: no feasible allocation (floors exceed the allocable water)');
  return (best as number[]).map(round6);
}

/** §2.3 sufficientarian — floor·D_i for all (cut by the table's ADR 0003 rule if short), remainder by a secondary rule. */
export function sufficientarian(schemes: Scheme[], allocable: number, params: LensParams, survivalFloor: number): number[] {
  const lens: LensId = 'sufficientarian';
  const D = schemes.map(s => s.demandMm3);
  const floors = D.map(d => need(params, 'floor', lens) * d);
  const sumFloors = floors.reduce((a, b) => a + b, 0);
  if (sumFloors >= allocable) {
    const rule = need(params, 'floorScaling', lens);
    if (!(rule in FLOOR_RULES)) throw new Error(`sufficientarian: unknown floorScaling '${rule}'`);
    const onFloors = schemes.map((s, i) => ({ ...s, demandMm3: at(floors, i) }));
    return allocate(FLOOR_RULES[rule], onFloors, allocable, params, survivalFloor).Q;
  }
  const secondary = need(params, 'secondary', lens);
  if (secondary === 'max_value') return maxValue(schemes, allocable, survivalFloor, floors);
  const residual = D.map((d, i) => d - at(floors, i));
  const weights = secondary === 'prioritarian' ? weightsFor('prioritarian', schemes, params) : residual;
  const extra = weightedCEA(residual, weights, allocable - sumFloors);
  return floors.map((f, i) => round6(f + at(extra, i)));
}

/** §2.3 weights C_i of the weighted-CEA lenses. */
export function weightsFor(lens: LensId, s: Scheme[], params: LensParams): number[] {
  switch (lens) {
    case 'egalitarian': return s.map(() => 1);
    case 'proportional': return s.map(x => x.demandMm3);
    case 'weighted_utilitarian': return s.map(x => (x.price * x.capacityT) / x.demandMm3); // ADR 0007: value productivity
    case 'capability': return s.map(x => x.people * x.kappa);
    case 'prioritarian': {
      // Q_i ∝ w_i^(1/γ) · D_i^(1−1/γ)
      const gamma = need(params, 'gamma', lens); const weight = need(params, 'weight', lens);
      if (!(gamma >= 1)) throw new Error(`prioritarian: gamma must be ≥ 1, got ${gamma}`);
      return s.map(x => Math.pow(weight === 'people' ? x.people : 1, 1 / gamma) * Math.pow(x.demandMm3, 1 - 1 / gamma));
    }
    default: throw new Error(`${lens} is not a weight rule`);
  }
}

/** Every lens of §2.3 except user-defined criteria (the §6.1 grammar). Surplus = max(0, AW − ΣD) (§2.6). */
export function allocate(lens: LensId, schemes: Scheme[], allocable: number, params: LensParams, survivalFloor: number): Allocation {
  const D = schemes.map(x => x.demandMm3);
  let Q: number[];
  if (lens === 'equal_sacrifice') Q = cel(D, allocable);
  else if (lens === 'talmud') Q = talmud(D, allocable);
  else if (lens === 'utilitarian') Q = maxValue(schemes, allocable, survivalFloor);
  else if (lens === 'sufficientarian') Q = sufficientarian(schemes, allocable, params, survivalFloor);
  else Q = weightedCEA(D, weightsFor(lens, schemes, params), allocable);
  return { lens, Q, surplusToAquifer: round6(Math.max(0, allocable - D.reduce((a, b) => a + b, 0))) };
}
