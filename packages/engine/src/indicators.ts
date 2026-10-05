// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

// Mirror of packages/engine-py/src/fairflow_engine/indicators.py (ADR 0002).

import { valueOf } from './production.js';
import type { Scheme } from './types.js';

const sum = (a: number[]): number => a.reduce((x, y) => x + y, 0);
const mean = (a: number[]): number => sum(a) / a.length;
const clip = (x: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, x));

/** 1 − CV with the population SD (blueprint §2.5). Unbounded below; equal zeros count as perfectly equal. */
export function oneMinusCV(values: number[]): number {
  const m = mean(values);
  if (m === 0) return 1;
  return 1 - Math.sqrt(mean(values.map(v => (v - m) ** 2))) / m; // §2.5 population SD
}

/** Gini coefficient, Σ|x_i − x_j| / (2n² x̄), without small-sample correction. */
export function gini(values: number[]): number {
  const n = values.length; const m = mean(values);
  if (m === 0) return 0;
  let t = 0; for (const a of values) for (const b of values) t += Math.abs(a - b);
  return t / (2 * n * n * m); // §2.5 Gini definition
}

/** Gini with the n/(n − 1) correction, the figure §2.5 reports beside the equity needles. */
export const giniCorrected = (values: number[]): number => (gini(values) * values.length) / (values.length - 1);

export type Equalisandum = 'claimant' | 'hectare' | 'person';

/** E_PJ: proportional-justice equity on adequacy A = W/D (Cherry 2025 Eq. 3-13). */
export const equityPJ = (s: Scheme[], W: number[]): number => oneMinusCV(W.map((w, i) => w / s[i].demandMm3));

/** E_SE(u): strict-egalitarian equity on water per unit of the equalisandum (claimant, hectare or person). */
export function equitySE(s: Scheme[], W: number[], u: Equalisandum): number {
  const unit = (x: Scheme) => (u === 'hectare' ? x.areaHa : u === 'person' ? x.people : 1);
  return oneMinusCV(W.map((w, i) => w / unit(s[i])));
}

/**
 * F: realised economic water productivity over design productivity at full demand (§2.5).
 * `consumed` divides by Σ β W (the dial); `diverted` drops β (the debrief toggle). F = 1 at full demand.
 */
export function efficiency(s: Scheme[], W: number[], basis: 'consumed' | 'diverted', survivalFloor: number): number {
  const b = (x: Scheme) => (basis === 'consumed' ? x.beta : 1);
  const used = sum(W.map((w, i) => b(s[i]) * w));
  if (used === 0) return 0;
  const realised = sum(W.map((w, i) => valueOf(s[i], w, survivalFloor))) / used;
  const design = sum(s.map(x => x.price * x.capacityT)) / sum(s.map(x => b(x) * x.demandMm3));
  return realised / design;
}

/** S: consumptive use over renewable supply, Σ β W / (β* AW + r₀), β* the demand-weighted mean β (§2.5). */
export function sustainability(s: Scheme[], W: number[], allocable: number, naturalRecharge: number): number {
  const betaStar = sum(s.map(x => x.beta * x.demandMm3)) / sum(s.map(x => x.demandMm3));
  return sum(W.map((w, i) => s[i].beta * w)) / (betaStar * allocable + naturalRecharge);
}

/** Triangle vertices (§2.5): r₁ = E_PJ clipped to [0, 1], r₂ = min(F, 1), r₃ = 1 − clip((S − 1)/ramp, 0, 1). */
export function triangle(ePJ: number, F: number, S: number, r3Ramp: number): { r1: number; r2: number; r3: number; area: number; score: number } {
  const r1 = clip(ePJ, 0, 1), r2 = clip(F, 0, 1), r3 = 1 - clip((S - 1) / r3Ramp, 0, 1);
  return { r1, r2, r3, area: (Math.sqrt(3) / 4) * (r1 * r2 + r2 * r3 + r3 * r1), score: Math.cbrt(r1 * r2 * r3) }; // §2.5 triangle
}

/** Collective score (R14): mean over seasons of the per-season geometric mean. */
export const collectiveScore = (seasonScores: number[]): number => (seasonScores.length ? mean(seasonScores) : 0);
