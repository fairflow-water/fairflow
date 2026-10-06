// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Test support: parameters come from the sourced registry (packages/scenarios/parameters.json), never from test code.

import type { LensParams } from './allocate.js';
import type { SeasonInput } from './resolveSeason.js';
import type { LensId } from './types.js';
import registryFile from '../../scenarios/parameters.json' with { type: 'json' };

const REGISTRY: Record<string, unknown> = Object.fromEntries(registryFile.parameters.map(p => [p.key, p.default]));

export const registry = (key: string): unknown => {
  if (!(key in REGISTRY)) throw new Error(`registry has no ${key}`);
  return REGISTRY[key];
};

export function lensParams(lens: LensId, overrides: LensParams = {}): LensParams {
  const collect = (l: string) => Object.fromEntries(
    Object.entries(REGISTRY).filter(([k]) => k.startsWith(`lenses.${l}.`)).map(([k, v]) => [k.slice(`lenses.${l}.`.length), v]));
  const base = lens === 'sufficientarian' ? { ...collect('prioritarian'), ...collect(lens) } : collect(lens);
  return { ...base, ...overrides } as LensParams;
}

export const scoring = (): SeasonInput['scoring'] => ({
  r3Ramp: registry('indicators.r3Ramp') as number,
  welfareGamma: registry('indicators.welfareGamma') as number,
  survivalFloor: registry('indicators.survivalFloor') as number,
  welfareSupplyFloor: registry('indicators.welfareSupplyFloor') as number,
  sustainabilityBands: registry('indicators.sustainabilityBands') as number[],
});
