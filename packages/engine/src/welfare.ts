// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import { gini } from './indicators.js';
import type { Scheme } from './types.js';

export interface Welfare { UWF: number; PWF: number; PWFede: number; SWF: number; EWF: number; CWF: number }

/**
 * Blueprint §2.7 — a posteriori welfare functions over s_i = min(A_i, 1) floored at 0.01.
 * PWF is Atkinson's isoelastic form on supply (increasing in supply); PWFede is its equally-distributed-equivalent
 * supply ratio on [0, 1], the display value. SWF is 0 if any s_i < m. EWF = 1 − Gini(s), uncorrected, which is what
 * the §3.1 fixtures use. Compare each function across lenses, never one function against another.
 */
export function welfare(schemes: Scheme[], A: number[], opts: { gamma: number; floor: number }): Welfare {
  const { gamma, floor: m } = opts;
  const n = A.length;
  const s = A.map(a => Math.max(0.01, Math.min(a, 1)));
  const UWF = s.reduce((t, x) => t + x, 0) / n;
  let PWF: number, PWFede: number;
  if (gamma === 1) {
    PWF = s.reduce((t, x) => t + Math.log(x), 0);
    PWFede = Math.exp(PWF / n);
  } else {
    PWF = s.reduce((t, x) => t + x ** (1 - gamma) / (1 - gamma), 0);
    PWFede = (((1 - gamma) * PWF) / n) ** (1 / (1 - gamma));
  }
  const SWF = s.some(x => x < m) ? 0 : (s.reduce((t, x) => t + Math.min(1, x / m), 0) + s.reduce((t, x) => t + (x - m) / (1 - m), 0)) / (2 * n);
  const EWF = 1 - gini(s);
  const N = schemes.map(x => x.people);
  const CWF = s.reduce((t, x, i) => t + N[i] * x, 0) / N.reduce((a, b) => a + b, 0);
  return { UWF, PWF, PWFede, SWF, EWF, CWF };
}
