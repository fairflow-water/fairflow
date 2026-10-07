// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT

import { allocate, type LensParams } from './allocate.js';
import { aquiferFull, aquiferSpill, inflowLossNext, nextStock, observedStock, pumpCostPerMm3, rationPumps, returnFlow } from './aquifer.js';
import { efficiency, equityPJ, equitySE, gini, giniCorrected, sustainability, sustainabilityBand, triangle } from './indicators.js';
import { yieldOf } from './production.js';
import { at, round6, type Allocation, type Basin, type LensId, type Scheme } from './types.js';
import { welfare, type Welfare } from './welfare.js';

export interface SeasonInput {
  schemes: Scheme[];
  basin: Basin;
  inflow: number;           // this season's card inflow, already reduced by GW–SW coupling
  stock: number;            // aquifer B_t at the start of the season
  lens: LensId;
  lensParams: LensParams;
  pumps: number[];          // requested pumping per scheme, 0..cap
  scoring: { r3Ramp: number; welfareGamma: number; survivalFloor: number; welfareSupplyFloor: number; sustainabilityBands: number[] };
}

export interface SeasonResult {
  observedStockNext: number;
  aquiferFull: boolean;
  asAllocated: { ePJ: number; eSE: { claimant: number; hectare: number; person: number }; F: { consumed: number; diverted: number } };
  sustainabilityBand: 'good' | 'warning' | 'unsustainable';
  allocable: number; allocation: Allocation;
  pumpCost: number[]; P: number[]; W: number[]; A: number[]; Y: number[]; dL: number[];
  pumpsTotal: number; returnFlow: number; stockNext: number; spill: number; inflowLossNext: number;
  ePJ: number; eSE: { claimant: number; hectare: number; person: number };
  gini: number; giniCorrected: number;
  F: { consumed: number; diverted: number }; S: number;
  triangle: { r1: number; r2: number; r3: number; area: number; score: number };
  welfare: Welfare;
}

/**
 * Blueprint R9–R12 for one season without actions, modules or events (those arrive with applyEvent):
 * allocate, ration the pumps, deliver, produce, score, and step the aquifer. Pure; every output rounded to 1e-6.
 */
export function resolveSeason(input: SeasonInput): SeasonResult {
  const { schemes: s, basin, stock } = input;
  const allocable = Math.max(0, input.inflow - basin.reserve);
  const floor = input.scoring.survivalFloor;
  const allocation = allocate(input.lens, s, allocable, input.lensParams, floor);
  const pumpCost = s.map(x => pumpCostPerMm3(basin, stock, x.seat));
  const P = rationPumps(basin, stock, input.pumps);
  const W = allocation.Q.map((q, i) => q + at(P, i));
  const A = W.map((w, i) => w / at(s, i).demandMm3);
  const Y = W.map((w, i) => yieldOf(at(s, i), w, floor));
  const dL = Y.map((y, i) => (at(s, i).price * y) / 100 - at(pumpCost, i) * at(P, i)); // §2.4 ΔL = pY/100 − c_p P
  const pumpsTotal = P.reduce((a, b) => a + b, 0);
  const returns = returnFlow(s, W);
  const stockNext = nextStock(basin, stock, allocation.surplusToAquifer, returns, pumpsTotal);
  const spill = aquiferSpill(basin, stock, allocation.surplusToAquifer, returns, pumpsTotal);
  const ePJ = equityPJ(s, W);
  const F = { consumed: efficiency(s, W, 'consumed', floor), diverted: efficiency(s, W, 'diverted', floor) };
  const S = sustainability(s, W, allocable, basin.aquifer.naturalRecharge);
  const sCapped = A.map(a => Math.max(input.scoring.welfareSupplyFloor, Math.min(a, 1)));
  const Q = allocation.Q; // ADR 0004: the in-play dials, on the public allocation only
  const r = round6;
  const tri = triangle(ePJ, F.consumed, S, input.scoring.r3Ramp);
  const wf = welfare(s, A, { gamma: input.scoring.welfareGamma, floor, supplyFloor: input.scoring.welfareSupplyFloor });
  return {
    observedStockNext: r(observedStock(basin, stockNext)),
    aquiferFull: aquiferFull(basin, stockNext),
    asAllocated: {
      ePJ: r(equityPJ(s, Q)),
      eSE: { claimant: r(equitySE(s, Q, 'claimant')), hectare: r(equitySE(s, Q, 'hectare')), person: r(equitySE(s, Q, 'person')) },
      F: { consumed: r(efficiency(s, Q, 'consumed', floor)), diverted: r(efficiency(s, Q, 'diverted', floor)) },
    },
    sustainabilityBand: sustainabilityBand(S, input.scoring.sustainabilityBands),
    allocable: r(allocable), allocation,
    pumpCost: pumpCost.map(r), P: P.map(r), W: W.map(r), A: A.map(r), Y: Y.map(r), dL: dL.map(r),
    pumpsTotal: r(pumpsTotal), returnFlow: r(returns), stockNext: r(stockNext), spill: r(spill), inflowLossNext: r(inflowLossNext(basin, stockNext)),
    ePJ: r(ePJ), eSE: { claimant: r(equitySE(s, W, 'claimant')), hectare: r(equitySE(s, W, 'hectare')), person: r(equitySE(s, W, 'person')) },
    gini: r(gini(sCapped)), giniCorrected: r(giniCorrected(sCapped)),
    F: { consumed: r(F.consumed), diverted: r(F.diverted) }, S: r(S),
    triangle: { r1: r(tri.r1), r2: r(tri.r2), r3: r(tri.r3), area: r(tri.area), score: r(tri.score) },
    welfare: { UWF: r(wf.UWF), PWF: r(wf.PWF), PWFede: r(wf.PWFede), SWF: r(wf.SWF), EWF: r(wf.EWF), CWF: r(wf.CWF) },
  };
}
