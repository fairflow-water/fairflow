// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
import { describe, expect, it } from 'vitest';
import { allocate, type LensParams } from './allocate.js';
import { valueOf, yieldOf } from './production.js';
import type { LensId, Scheme } from './types.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };

const schemes = fixtures.schemes as Scheme[];
type Row = { lens: string; params?: LensParams; Q: number[]; Y?: number[] };

const years: [string, number, Row[]][] = [
  ['blueprint §3.1 dry year, AW = 10', 10, fixtures.dry as Row[]],
  ['blueprint §3.2 normal year, AW = 15', 15, fixtures.normal as Row[]],
];

for (const [title, AW, rows] of years) {
  describe(title, () => {
    for (const row of rows) {
      it(row.lens, () => {
        const { Q } = allocate(row.lens as LensId, schemes, AW, row.params);
        Q.forEach((q, i) => expect(q).toBeCloseTo(row.Q[i], 2));
        // Y fixtures are rounded to the tonne and computed from two-decimal Q, hence the 2 t tolerance.
        row.Y?.forEach((y, i) => expect(Math.abs(yieldOf(schemes[i], Q[i]) - y)).toBeLessThan(2));
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

describe('blueprint §3.2 normal-year coincidences', () => {
  const Q = (lens: LensId) => allocate(lens, schemes, 15).Q;
  it('utilitarian = weighted utilitarian', () => expect(Q('utilitarian')).toEqual(Q('weighted_utilitarian')));
  it('sufficientarian = utilitarian (every floor met first)', () => expect(Q('sufficientarian')).toEqual(Q('utilitarian')));
  it('equal sacrifice = Talmud', () => expect(Q('equal_sacrifice')).toEqual(Q('talmud')));
});

describe('blueprint §9.1 allocation properties (seeded random basins)', () => {
  let seed = 20261005;
  const rand = () => ((seed = (seed * 48271) % 2147483647) / 2147483647); // Park–Miller, exact in doubles
  const randomBasin = (): Scheme[] => Array.from({ length: 3 + Math.floor(rand() * 3) }, (_, i) => ({
    id: String(i), name: String(i), seat: i + 1, demandMm3: 1 + rand() * 9, capacityT: 500 + rand() * 5000,
    ky: 0.5 + rand() * 0.8, beta: 1, people: 10 + rand() * 2000, kappa: 1, price: 0.5 + rand(), areaHa: 100 + rand() * 900,
  }));
  const lenses: LensId[] = ['utilitarian', 'weighted_utilitarian', 'egalitarian', 'proportional', 'capability', 'sufficientarian', 'prioritarian', 'equal_sacrifice', 'talmud'];
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);

  it('every lens: Σ Q = min(AW, Σ D) and 0 ≤ Q_i ≤ D_i', () => {
    for (let g = 0; g < 200; g++) {
      const s = randomBasin(); const AW = rand() * sum(s.map(x => x.demandMm3)) * 1.2;
      for (const lens of lenses) {
        const { Q } = allocate(lens, s, AW);
        expect(Math.abs(sum(Q) - Math.min(AW, sum(s.map(x => x.demandMm3))))).toBeLessThan(1e-5);
        Q.forEach((q, i) => { expect(q).toBeGreaterThanOrEqual(0); expect(q).toBeLessThanOrEqual(s[i].demandMm3 + 1e-6); });
      }
    }
  });

  it('the maximiser is never beaten by 10,000 random feasible allocations', () => {
    for (let g = 0; g < 10; g++) {
      const s = randomBasin(); const D = s.map(x => x.demandMm3); const AW = rand() * sum(D);
      const best = sum(allocate('utilitarian', s, AW).Q.map((q, i) => valueOf(s[i], q)));
      for (let t = 0; t < 1000; t++) {
        const share = D.map(() => rand()); const Q = new Array<number>(D.length).fill(0); let left = AW;
        for (let pass = 0; pass < 10 && left > 1e-9; pass++) {
          const open = D.map((d, i) => d - Q[i]); const w = sum(share.map((x, i) => (open[i] > 0 ? x : 0)));
          if (w === 0) break;
          const before = left;
          share.forEach((x, i) => { if (open[i] > 0) { const add = Math.min(open[i], (x / w) * before); Q[i] += add; left -= add; } });
        }
        expect(sum(Q.map((q, i) => valueOf(s[i], q)))).toBeLessThanOrEqual(best + 1e-3);
      }
    }
  });
});
