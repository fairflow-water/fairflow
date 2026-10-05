// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
import { describe, expect, it } from 'vitest';
import { allocate, type LensParams } from './allocate.js';
import type { LensId, Scheme } from './types.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };

const schemes = fixtures.schemes as Scheme[];
const notInScaffold = new Set(['utilitarian', 'sufficientarian']);
type Row = { lens: string; params?: LensParams; Q: number[] };

const years: [string, number, Row[]][] = [
  ['blueprint §3.1 dry year, AW = 10', 10, fixtures.dry as Row[]],
  ['blueprint §3.2 normal year, AW = 15', 15, fixtures.normal as Row[]],
];

for (const [title, AW, rows] of years) {
  describe(title, () => {
    for (const row of rows) {
      it.skipIf(notInScaffold.has(row.lens))(row.lens, () => {
        const { Q } = allocate(row.lens as LensId, schemes, AW, row.params);
        Q.forEach((q, i) => expect(q).toBeCloseTo(row.Q[i], 2));
      });
    }
  });
}

describe('blueprint §3.3 prioritarian limits', () => {
  const egal = allocate('egalitarian', schemes, 10).Q;
  const prop = allocate('proportional', schemes, 10).Q;
  it('γ → 1 gives strict egalitarian', () => {
    allocate('prioritarian', schemes, 10, { gamma: 1.001 }).Q.forEach((q, i) => expect(Math.abs(q - egal[i])).toBeLessThan(0.01));
  });
  it('γ → ∞ gives proportional', () => {
    allocate('prioritarian', schemes, 10, { gamma: 1000 }).Q.forEach((q, i) => expect(Math.abs(q - prop[i])).toBeLessThan(0.01));
  });
  it('rejects γ < 1', () => {
    expect(() => allocate('prioritarian', schemes, 10, { gamma: 0.5 })).toThrow();
  });
});
