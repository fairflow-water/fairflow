// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Input validation at the `engine serve` boundary (OWASP: validate untrusted input into typed values before use).
// Every check names the path of the offending field, so a client can fix its message.

import { FLOOR_RULES, type FloorRule, type LensParams } from './allocate.js';
import type { SeasonInput } from './resolveSeason.js';
import type { Basin, LensId, Scheme } from './types.js';

/** A message that does not have the shape the protocol requires. */
export class InputError extends Error {}

type Json = Record<string, unknown>;
const LENS_IDS: readonly LensId[] = ['utilitarian', 'weighted_utilitarian', 'egalitarian', 'proportional', 'capability',
  'sufficientarian', 'prioritarian', 'equal_sacrifice', 'talmud'];

export function object(value: unknown, path: string): Json {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new InputError(`${path}: expected an object`);
  return value as Json;
}

export function number(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new InputError(`${path}: expected a finite number`);
  return value;
}

export function string(value: unknown, path: string): string {
  if (typeof value !== 'string') throw new InputError(`${path}: expected a string`);
  return value;
}

export function array(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new InputError(`${path}: expected an array`);
  return value;
}

export const numbers = (value: unknown, path: string): number[] => array(value, path).map((v, i) => number(v, `${path}[${i}]`));

export function lensId(value: unknown, path: string): LensId {
  const s = string(value, path);
  if (!(LENS_IDS as readonly string[]).includes(s)) throw new InputError(`${path}: unknown lens "${s}"`);
  return s as LensId;
}

export function scheme(value: unknown, path: string): Scheme {
  const o = object(value, path);
  return {
    id: string(o['id'], `${path}.id`), name: string(o['name'], `${path}.name`), seat: number(o['seat'], `${path}.seat`),
    demandMm3: number(o['demandMm3'], `${path}.demandMm3`), capacityT: number(o['capacityT'], `${path}.capacityT`),
    ky: number(o['ky'], `${path}.ky`), beta: number(o['beta'], `${path}.beta`), people: number(o['people'], `${path}.people`),
    kappa: number(o['kappa'], `${path}.kappa`), price: number(o['price'], `${path}.price`), areaHa: number(o['areaHa'], `${path}.areaHa`),
    pumpCostFactor: o['pumpCostFactor'] === undefined ? 1 : number(o['pumpCostFactor'], `${path}.pumpCostFactor`),
    wellsFailAtOrBelow: o['wellsFailAtOrBelow'] === undefined || o['wellsFailAtOrBelow'] === null ? null : number(o['wellsFailAtOrBelow'], `${path}.wellsFailAtOrBelow`),
  };
}

export const schemes = (value: unknown, path: string): Scheme[] => array(value, path).map((v, i) => scheme(v, `${path}[${i}]`));

export function basin(value: unknown, path: string): Basin {
  const o = object(value, path);
  const a = object(o['aquifer'], `${path}.aquifer`);
  const p = object(o['pump'], `${path}.pump`);
  return {
    reserve: number(o['reserve'], `${path}.reserve`),
    aquifer: {
      initial: number(a['initial'], `${path}.aquifer.initial`), reserve: number(a['reserve'], `${path}.aquifer.reserve`),
      lowThreshold: number(a['lowThreshold'], `${path}.aquifer.lowThreshold`),
      naturalRecharge: number(a['naturalRecharge'], `${path}.aquifer.naturalRecharge`),
      seatCostMultipliers: numbers(a['seatCostMultipliers'], `${path}.aquifer.seatCostMultipliers`),
      maxInflowLossMm3: number(a['maxInflowLossMm3'], `${path}.aquifer.maxInflowLossMm3`),
      tankResolution: number(a['tankResolution'], `${path}.aquifer.tankResolution`),
      capacity: a['capacity'] === undefined || a['capacity'] === null ? null : number(a['capacity'], `${path}.aquifer.capacity`),
      returnRecharge: a['returnRecharge'] === undefined ? 1 : number(a['returnRecharge'], `${path}.aquifer.returnRecharge`),
      baseflowLossPerMm3: a['baseflowLossPerMm3'] === undefined || a['baseflowLossPerMm3'] === null ? null : number(a['baseflowLossPerMm3'], `${path}.aquifer.baseflowLossPerMm3`),
    },
    pump: { cap: number(p['cap'], `${path}.pump.cap`), costBase: number(p['costBase'], `${path}.pump.costBase`),
      costSlope: number(p['costSlope'], `${path}.pump.costSlope`),
      capShare: p['capShare'] === undefined || p['capShare'] === null ? null : number(p['capShare'], `${path}.pump.capShare`) },
  };
}

export function scoring(value: unknown, path: string): SeasonInput['scoring'] {
  const o = object(value, path);
  return {
    r3Ramp: number(o['r3Ramp'], `${path}.r3Ramp`), welfareGamma: number(o['welfareGamma'], `${path}.welfareGamma`),
    survivalFloor: number(o['survivalFloor'], `${path}.survivalFloor`),
    welfareSupplyFloor: number(o['welfareSupplyFloor'], `${path}.welfareSupplyFloor`),
    sustainabilityBands: numbers(o['sustainabilityBands'], `${path}.sustainabilityBands`),
  };
}

/** Lens parameters: optional by design (each lens checks what it needs); present ones must be well-typed. */
export function lensParams(value: unknown, path: string): LensParams {
  if (value === undefined) return {};
  const o = object(value, path);
  const out: LensParams = {};
  if (o['gamma'] !== undefined) out.gamma = number(o['gamma'], `${path}.gamma`);
  if (o['floor'] !== undefined) out.floor = number(o['floor'], `${path}.floor`);
  if (o['weight'] !== undefined) {
    const w = string(o['weight'], `${path}.weight`);
    if (w !== '1' && w !== 'people') throw new InputError(`${path}.weight: expected "1" or "people"`);
    out.weight = w;
  }
  if (o['floorScaling'] !== undefined) {
    const f = string(o['floorScaling'], `${path}.floorScaling`);
    if (!(f in FLOOR_RULES)) throw new InputError(`${path}.floorScaling: unknown rule "${f}"`);
    out.floorScaling = f as FloorRule;
  }
  if (o['secondary'] !== undefined) {
    const s = string(o['secondary'], `${path}.secondary`);
    if (s !== 'max_value' && s !== 'prioritarian' && s !== 'proportional') throw new InputError(`${path}.secondary: unknown rule "${s}"`);
    out.secondary = s;
  }
  return out;
}

export function seasonInput(o: Json): SeasonInput {
  return {
    schemes: schemes(o['schemes'], 'schemes'), basin: basin(o['basin'], 'basin'), inflow: number(o['inflow'], 'inflow'),
    stock: number(o['stock'], 'stock'), lens: lensId(o['lens'], 'lens'), lensParams: lensParams(o['lensParams'], 'lensParams'),
    pumps: numbers(o['pumps'], 'pumps'), scoring: scoring(o['scoring'], 'scoring'),
  };
}
