// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
import { describe, expect, it } from 'vitest';
import type { LensParams } from './allocate.js';
import { inflowLossNext, pumpCostPerMm3 } from './aquifer.js';
import { equityPJ, equitySE } from './indicators.js';
import { resolveSeason, type SeasonInput } from './resolveSeason.js';
import type { Basin, LensId, Scheme } from './types.js';
import { verdict } from './verdict.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };
import betaFixtures from '../fixtures/default-basin-beta.json' with { type: 'json' };

const schemes = fixtures.schemes as Scheme[];
const basin = fixtures.basin as Basin;
const inflow = fixtures.basin.inflow;
const scoring = fixtures.scoring;
const LENSES: LensId[] = ['utilitarian', 'weighted_utilitarian', 'egalitarian', 'proportional', 'capability', 'sufficientarian', 'prioritarian', 'equal_sacrifice', 'talmud'];
const zero = () => schemes.map(() => 0);
const season = (over: Partial<SeasonInput>) => resolveSeason({ schemes, basin, inflow: inflow.normal, stock: basin.aquifer.initial, lens: 'proportional', pumps: zero(), scoring, ...over });
/** Fixtures are printed to two decimals, or to one for |x| ≥ 10 (the large PWF₃ sums); exact halves (0.525) round either way. */
const close = (got: number, want: number) => expect(Math.abs(got - want)).toBeLessThanOrEqual((Math.abs(want) >= 10 ? 0.05 : 0.005) + 1e-9);

type Row = { lens: string; params?: LensParams; ePJ: number; eSE: number; F: number;
  welfare?: { UWF: number; PWF3: number; EWF: number; CWF: number; SWF: number } };

for (const [year, rows] of [['dry', fixtures.dry], ['normal', fixtures.normal]] as [keyof typeof inflow, Row[]][]) {
  describe(`blueprint §3 ${year} year: indicators and welfare (v1 reduction)`, () => {
    for (const row of rows) {
      it(row.lens, () => {
        const r = season({ inflow: inflow[year], lens: row.lens as LensId, lensParams: row.params });
        close(r.ePJ, row.ePJ); close(r.eSE.claimant, row.eSE); close(r.F.consumed, row.F);
        close(r.S, 1); expect(r.triangle.r3).toBe(1);
        if (row.welfare) {
          close(r.welfare.UWF, row.welfare.UWF); close(r.welfare.PWF, row.welfare.PWF3); close(r.welfare.EWF, row.welfare.EWF);
          close(r.welfare.CWF, row.welfare.CWF); close(r.welfare.SWF, row.welfare.SWF);
        }
      });
    }
  });
}

describe('blueprint §3 wet year', () => {
  for (const lens of LENSES) {
    it(lens, () => {
      const r = season({ inflow: inflow.wet, lens });
      r.allocation.Q.forEach((q, i) => close(q, fixtures.wet.Q[i]));
      close(r.allocation.surplusToAquifer, fixtures.wet.surplusToAquifer);
      expect(r.Y.reduce((a, b) => a + b, 0)).toBeCloseTo(fixtures.wet.sumY, 6);
      close(r.ePJ, fixtures.wet.ePJ); close(r.eSE.claimant, fixtures.wet.eSE); close(r.F.consumed, fixtures.wet.F); close(r.S, fixtures.wet.S);
    });
  }
});

describe('blueprint §3.3 dynamic fixtures', () => {
  it('pumping: normal, proportional, each pumps 2', () => {
    const r = season({ pumps: [2, 2, 2] });
    [7.03, 9.24, 4.73].forEach((w, i) => close(r.W[i], w));
    r.A.forEach(a => expect(a).toBeGreaterThanOrEqual(1));
    expect(r.Y.reduce((a, b) => a + b, 0)).toBeCloseTo(11500, 6);
    close(r.F.consumed, 0.89); close(r.S, 1.40); close(r.triangle.r3, 0.33);
    expect(r.stockNext).toBe(14);
    r.pumpCost.forEach(c => expect(c * 2).toBe(4));
  });

  it('depletion: dry, dry, normal, each pumps 2; B = 14, 8, 5; season 3 rations 6 requests to 3', () => {
    let stock = basin.aquifer.initial; let loss = 0; const stocks: number[] = []; let last;
    for (const card of ['dry', 'dry', 'normal'] as const) {
      last = season({ inflow: inflow[card] - loss, stock, pumps: [2, 2, 2] });
      stock = last.stockNext; loss = last.inflowLossNext; stocks.push(stock);
    }
    expect(stocks).toEqual([14, 8, 5]);
    last!.P.forEach(p => expect(p).toBeCloseTo(1, 6));
  });

  it('pump cost per Mm³ at B = 14, 8, 5 is 3.8, 5.6, 6.5 before seat multipliers (§3.4: 8.4 and 11.2 for B and C at 8)', () => {
    close(pumpCostPerMm3(basin, 14, 1), 3.8); close(pumpCostPerMm3(basin, 8, 1), 5.6); close(pumpCostPerMm3(basin, 5, 1), 6.5);
    close(pumpCostPerMm3(basin, 8, 2), 8.4); close(pumpCostPerMm3(basin, 8, 3), 11.2);
    expect(pumpCostPerMm3(basin, 20, 3)).toBe(2);
  });

  it('natural recharge: B_{t+1} = B_t + surplus + r₀ − ΣP', () => {
    const b: Basin = { ...basin, aquifer: { ...basin.aquifer, naturalRecharge: 1 } };
    const r = resolveSeason({ schemes, basin: b, inflow: inflow.wet, stock: 12, lens: 'egalitarian', pumps: [0, 1, 0], scoring });
    close(r.stockNext, 12 + 1.35 + 1 - 1);
  });

  it('return flow (β set): normal, proportional, aquifer gains 0.50 + 2.90 + 0.68 = 4.08 plus r₀', () => {
    const beta = [0.9, 0.6, 0.75];
    const s = schemes.map((x, i) => ({ ...x, beta: beta[i] }));
    const b: Basin = { ...basin, aquifer: { ...basin.aquifer, naturalRecharge: 1 } };
    const r = resolveSeason({ schemes: s, basin: b, inflow: inflow.normal, stock: 20, lens: 'proportional', pumps: zero(), scoring });
    close(r.returnFlow, 4.08);
    close(r.stockNext, 20 + 4.08 + 1);
  });

  it('GW–SW coupling: B falls to 8, next inflow reduced by 0.2', () => close(inflowLossNext(basin, 8), 0.2));

  it('equalisandum: dry, proportional; per claimant 0.63, per hectare 1.00, per person 0.35', () => {
    const r = season({ inflow: inflow.dry });
    close(r.eSE.claimant, 0.63); close(r.eSE.hectare, 1.0); close(r.eSE.person, 0.35);
  });

  it('§3.4 capability (κ = 1) drives E_PJ below zero while per-person E_SE is highest (0.75)', () => {
    const r = season({ inflow: inflow.dry, lens: 'capability' });
    expect(r.ePJ).toBeLessThan(0); close(r.eSE.person, 0.75);
    for (const lens of LENSES) expect(season({ inflow: inflow.dry, lens }).eSE.person).toBeLessThanOrEqual(r.eSE.person);
  });

  it('verdict match: dry, proportional voted; verdict matches the vote, pumping gap 0', () => {
    const r = season({ inflow: inflow.dry });
    const v = verdict(schemes, r.allocable, r.W, 'proportional', r.pumpsTotal, LENSES.map(id => ({ id })));
    expect(v).toMatchObject({ voted: 'proportional', satisfied: 'proportional', pumpingGap: 0 });
    for (const lens of LENSES) expect(season({ inflow: inflow.dry, lens }).welfare.EWF).toBeLessThanOrEqual(r.welfare.EWF);
  });

  it('verdict mismatch: dry, utilitarian voted; highest UWF of any lens, lowest PWF₃ and CWF, SWF 0', () => {
    const all = LENSES.map(lens => season({ inflow: inflow.dry, lens, lensParams: lens === 'prioritarian' ? { gamma: 3 } : undefined }));
    const u = all[0];
    for (const r of all) {
      expect(r.welfare.UWF).toBeLessThanOrEqual(u.welfare.UWF);
      expect(r.welfare.PWF).toBeGreaterThanOrEqual(u.welfare.PWF);
      expect(r.welfare.CWF).toBeGreaterThanOrEqual(u.welfare.CWF);
    }
    close(u.welfare.PWF, -331.6); expect(u.welfare.SWF).toBe(0);
  });
});

describe('blueprint §9.1 indicator properties (seeded random basins)', () => {
  let seed = 7;
  const rand = () => ((seed = (seed * 48271) % 2147483647) / 2147483647);
  const randomSchemes = (beta?: number): Scheme[] => Array.from({ length: 3 + Math.floor(rand() * 3) }, (_, i) => {
    const demandMm3 = 1 + rand() * 9;
    return { id: String(i), name: String(i), seat: i + 1, demandMm3, capacityT: 500 + rand() * 5000, ky: 0.5 + rand() * 0.8,
      beta: beta ?? 0.5 + rand() * 0.5, people: 10 + rand() * 2000, kappa: 1, price: 0.5 + rand(), areaHa: demandMm3 * 100 };
  });
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);

  it('F = 1 at full demand; E_PJ = 1 for proportional; per-hectare E_SE = E_PJ at uniform depth', () => {
    for (let g = 0; g < 100; g++) {
      const s = randomSchemes(); const D = s.map(x => x.demandMm3);
      const full = resolveSeason({ schemes: s, basin, inflow: basin.reserve + sum(D) * (1 + rand()), stock: 20, lens: 'egalitarian', pumps: s.map(() => 0), scoring });
      close(full.F.consumed, 1); close(full.F.diverted, 1);
      const W = D.map(d => d * rand());
      const prop = resolveSeason({ schemes: s, basin, inflow: basin.reserve + sum(W), stock: 20, lens: 'proportional', pumps: s.map(() => 0), scoring });
      close(prop.ePJ, 1);
      expect(equitySE(s, W, 'hectare')).toBeCloseTo(equityPJ(s, W), 9);
    }
  });

  it('E_SE per claimant = 1 for equal shares when uncapped', () => {
    for (let g = 0; g < 100; g++) {
      const s = randomSchemes(); const AW = Math.min(...s.map(x => x.demandMm3)) * s.length * rand();
      close(resolveSeason({ schemes: s, basin, inflow: basin.reserve + AW, stock: 20, lens: 'egalitarian', pumps: s.map(() => 0), scoring }).eSE.claimant, 1);
    }
  });

  it('S > 1 iff Σ P > r₀ in a season with no surplus (β = 1, the condition under which the property holds exactly)', () => {
    for (let g = 0; g < 200; g++) {
      const s = randomSchemes(1); const r0 = rand() * 2;
      const b: Basin = { ...basin, aquifer: { ...basin.aquifer, naturalRecharge: r0 } };
      const AW = sum(s.map(x => x.demandMm3)) * rand(); const pumps = s.map(() => (rand() < 0.5 ? 0 : rand() * 2));
      const r = resolveSeason({ schemes: s, basin: b, inflow: basin.reserve + AW, stock: 20, lens: 'proportional', pumps, scoring });
      if (Math.abs(r.pumpsTotal - r0) > 1e-4) expect(r.S > 1).toBe(r.pumpsTotal > r0);
    }
  });

  it('aquifer mass balance closes to 1e-6 every season', () => {
    for (let g = 0; g < 200; g++) {
      const s = randomSchemes(); const r0 = rand();
      const b: Basin = { ...basin, aquifer: { ...basin.aquifer, naturalRecharge: r0 } };
      const stock = 5 + rand() * 20; const AW = sum(s.map(x => x.demandMm3)) * 1.3 * rand();
      const r = resolveSeason({ schemes: s, basin: b, inflow: basin.reserve + AW, stock, lens: LENSES[g % LENSES.length], pumps: s.map(() => rand() * 2), scoring });
      const balance = stock + r.allocation.surplusToAquifer + r0 + r.returnFlow - r.pumpsTotal;
      expect(Math.abs(r.stockNext - Math.max(basin.aquifer.reserve, balance))).toBeLessThan(1e-5);
      expect(r.pumpsTotal).toBeLessThanOrEqual(Math.max(0, stock - basin.aquifer.reserve) + 1e-6);
    }
  });
});

describe('blueprint §3 β fixture set (β = 0.90 / 0.60 / 0.75, r₀ = 1)', () => {
  type BetaRow = { lens: LensId; params?: LensParams; Q: number[]; A: number[]; Y: number[]; ePJ: number; eSE: number;
    F: { consumed: number; diverted: number }; S: number; r3: number; returnFlow: number; stockNext: number };
  const b = betaFixtures.basin as Basin; const s = betaFixtures.schemes as Scheme[];
  for (const card of ['wet', 'normal', 'dry'] as const) {
    for (const row of betaFixtures[card] as BetaRow[]) {
      it(`${card} ${row.lens}: engine reproduces the β set, and Q, A, Y, equity equal the v1 reduction`, () => {
        const r = resolveSeason({ schemes: s, basin: b, inflow: b.inflow[card], stock: b.aquifer.initial, lens: row.lens, lensParams: row.params, pumps: zero(), scoring });
        row.Q.forEach((q, i) => close(r.allocation.Q[i], q)); row.A.forEach((a, i) => close(r.A[i], a));
        row.Y.forEach((y, i) => expect(Math.abs(r.Y[i] - y)).toBeLessThanOrEqual(0.5 + 1e-9));
        close(r.F.consumed, row.F.consumed); close(r.F.diverted, row.F.diverted); close(r.S, row.S); close(r.triangle.r3, row.r3);
        close(r.returnFlow, row.returnFlow); close(r.stockNext, row.stockNext);
        const v1 = season({ inflow: inflow[card], lens: row.lens, lensParams: row.params });
        expect(r.allocation.Q).toEqual(v1.allocation.Q); expect(r.A).toEqual(v1.A); expect(r.Y).toEqual(v1.Y);
        expect(r.ePJ).toBe(v1.ePJ); expect(r.eSE).toEqual(v1.eSE);
      });
    }
  }
});
