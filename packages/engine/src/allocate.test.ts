// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Expected values come from fixtures/default-basin-v1.json, which CI checks against docs/blueprint.md (Python);
// parameters come from the registry. No model number is written in this file.

import { describe, expect, it } from 'vitest';
import { allocate, FLOOR_RULES, maxValue, MissingParameter, weightedCEA, type FloorRule, type LensParams } from './allocate.js';
import { valueOf } from './production.js';
import { lensParams, registry } from './registry.testutil.js';
import { at, type LensId, type Scheme } from './types.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };

const schemes = fixtures.schemes as Scheme[];
const floor = registry('indicators.survivalFloor') as number;
const LENSES: LensId[] = ['utilitarian', 'weighted_utilitarian', 'egalitarian', 'proportional', 'capability', 'sufficientarian', 'prioritarian', 'equal_sacrifice', 'talmud'];
type Row = { lens: LensId; params?: LensParams; Q: number[] };
const allocable = (card: 'dry' | 'normal') => fixtures.basin.inflow[card] - fixtures.basin.reserve;

/** Half a unit of the last printed digit; fixture Q values are printed to two decimals (§3). */
const printed = (x: number) => 0.5 * 10 ** -((String(x).split('.')[1] ?? '').length || 2);

for (const card of ['dry', 'normal'] as const) {
  describe(`blueprint §3 ${card} year allocations (v1 fixtures)`, () => {
    for (const row of fixtures[card] as Row[]) {
      it(row.lens, () => {
        const { Q } = allocate(row.lens, schemes, allocable(card), lensParams(row.lens, row.params), floor);
        Q.forEach((q, i) => expect(Math.abs(q - row.Q[i])).toBeLessThanOrEqual(printed(row.Q[i]) + 1e-9));
      });
    }
  });
}

describe('review E5: tied marginal values are left to the Python engine', () => {
  it('refuses rather than return a different optimum', () => {
    const s = at(schemes, 2);
    const same = ['X', 'Y', 'Z'].map(id => ({ ...s, id }));
    expect(() => maxValue(same, 7, 0.5)).toThrow(/tied marginal values/);
  });
});

describe('review E4: zero weights are refused, as in the Python engine', () => {
  it('throws instead of returning NaN', () => {
    expect(() => weightedCEA([3, 5], [0, 0], 6)).toThrow(/positive weight/);
    expect(weightedCEA([0, 5], [0, 1], 6)).toEqual([0, 5]);
  });
});

describe('blueprint §3.2 normal-year coincidences', () => {
  const Q = (lens: LensId) => allocate(lens, schemes, allocable('normal'), lensParams(lens), floor).Q;
  it('utilitarian = weighted utilitarian', () => expect(Q('utilitarian')).toEqual(Q('weighted_utilitarian')));
  it('sufficientarian = utilitarian (every floor met first)', () => expect(Q('sufficientarian')).toEqual(Q('utilitarian')));
  it('equal sacrifice = Talmud', () => expect(Q('equal_sacrifice')).toEqual(Q('talmud')));
});

describe('no defaults: a lens without its parameters is refused', () => {
  it('prioritarian without gamma', () => expect(() => allocate('prioritarian', schemes, allocable('dry'), { weight: '1' }, floor)).toThrow(MissingParameter));
  it('sufficientarian without floor', () => expect(() => allocate('sufficientarian', schemes, allocable('dry'), {}, floor)).toThrow(MissingParameter));
});

describe('§9.1 allocation properties and ADR 0003 floor rules (seeded random basins; draws are test inputs)', () => {
  let seed = 20261005;
  const rand = () => ((seed = (seed * 48271) % 2147483647) / 2147483647); // Park–Miller
  const randomBasin = (): Scheme[] => Array.from({ length: 3 + Math.floor(rand() * 3) }, (_, i) => ({
    id: String(i), name: String(i), seat: i + 1, demandMm3: 1 + rand() * 9, capacityT: 500 + rand() * 5000,
    ky: 0.5 + rand() * 0.8, beta: 1, people: 10 + rand() * 2000, kappa: 1, price: 0.5 + rand(), areaHa: 100 + rand() * 900,
  }));
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);

  for (const rule of Object.keys(FLOOR_RULES) as FloorRule[]) {
    it(`every lens: Σ Q = min(AW, Σ D) and 0 ≤ Q_i ≤ D_i (floorScaling ${rule})`, () => {
      for (let g = 0; g < 60; g++) {
        const s = randomBasin(); const D = s.map(x => x.demandMm3); const AW = rand() * sum(D) * 1.2;
        for (const lens of LENSES) {
          const { Q } = allocate(lens, s, AW, lensParams(lens, { floorScaling: rule }), floor);
          expect(Math.abs(sum(Q) - Math.min(AW, sum(D)))).toBeLessThan(1e-5);
          Q.forEach((q, i) => { expect(q).toBeGreaterThanOrEqual(0); expect(q).toBeLessThanOrEqual(D[i] + 1e-6); });
        }
      }
    });
  }

  it('the maximiser is never beaten by 10,000 random feasible allocations', () => {
    for (let g = 0; g < 10; g++) {
      const s = randomBasin(); const D = s.map(x => x.demandMm3); const AW = rand() * sum(D);
      const best = sum(allocate('utilitarian', s, AW, {}, floor).Q.map((q, i) => valueOf(s[i], q, floor)));
      const slope = Math.max(...s.map(x => Math.max(valueOf(x, floor * x.demandMm3, floor) / (floor * x.demandMm3),
        (valueOf(x, x.demandMm3, floor) - valueOf(x, floor * x.demandMm3, floor)) / ((1 - floor) * x.demandMm3))));
      const rounding = s.length * 0.5e-6 * slope; // Q is rounded to 1e-6 (§7.2)
      for (let t = 0; t < 1000; t++) {
        const share = D.map(() => rand()); const Q = new Array<number>(D.length).fill(0); let left = AW;
        for (let pass = 0; pass < D.length && left > 1e-9; pass++) {
          const open = D.map((d, i) => d - Q[i]); const w = sum(share.map((x, i) => (open[i] > 0 ? x : 0)));
          if (w === 0) break;
          const before = left;
          share.forEach((x, i) => { if (open[i] > 0) { const add = Math.min(open[i], (x / w) * before); Q[i] += add; left -= add; } });
        }
        expect(sum(Q.map((q, i) => valueOf(s[i], q, floor)))).toBeLessThanOrEqual(best + rounding);
      }
    }
  });
});
