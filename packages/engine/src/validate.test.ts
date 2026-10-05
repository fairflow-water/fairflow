// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
//
// The serve boundary rejects malformed input with the path of the offending field; values here are test inputs.

import { describe, expect, it } from 'vitest';
import { at } from './types.js';
import { InputError, basin, lensId, lensParams, numbers, object, scheme, seasonInput } from './validate.js';
import fixtures from '../fixtures/conformance.json' with { type: 'json' };

const good = (fixtures.cases[0] as unknown as { input: Record<string, unknown> }).input;
const rejects = (f: () => unknown, path: string) => {
  try { f(); } catch (e) {
    expect(e).toBeInstanceOf(InputError);
    expect((e as Error).message.startsWith(`${path}:`)).toBe(true);
    return;
  }
  throw new Error(`expected a rejection at ${path}`);
};

describe('validate', () => {
  it('accepts a well-formed season input unchanged in value', () => {
    expect(seasonInput(good)).toEqual(good);
  });
  it('names the path of a bad field', () => {
    const schemes = structuredClone(good['schemes']) as Record<string, unknown>[];
    (schemes[1] as Record<string, unknown>)['demandMm3'] = 'nine';
    rejects(() => seasonInput({ ...good, schemes }), 'schemes[1].demandMm3');
  });
  it('rejects non-finite numbers, wrong containers and unknown lenses', () => {
    rejects(() => numbers([1, Number.NaN], 'pumps'), 'pumps[1]');
    rejects(() => numbers({}, 'pumps'), 'pumps');
    rejects(() => object([], 'basin'), 'basin');
    rejects(() => lensId('fairest', 'lens'), 'lens');
    rejects(() => scheme(null, 'schemes[0]'), 'schemes[0]');
    rejects(() => basin({ ...(good['basin'] as object), aquifer: { tankResolution: 1 } }, 'basin'), 'basin.aquifer.initial');
  });
  it('lens parameters: absent is empty; present must be well-typed', () => {
    expect(lensParams(undefined, 'p')).toEqual({});
    expect(lensParams({ gamma: 3, weight: 'people', floor: 0.5, floorScaling: 'cea', secondary: 'max_value' }, 'p'))
      .toEqual({ gamma: 3, weight: 'people', floor: 0.5, floorScaling: 'cea', secondary: 'max_value' });
    rejects(() => lensParams({ weight: 'acres' }, 'p'), 'p.weight');
    rejects(() => lensParams({ floorScaling: 'lottery' }, 'p'), 'p.floorScaling');
    rejects(() => lensParams({ secondary: 'random' }, 'p'), 'p.secondary');
    rejects(() => lensParams({ gamma: '2' }, 'p'), 'p.gamma');
  });
  it('errors are InputError', () => {
    expect(() => lensId(7, 'lens')).toThrow(InputError);
  });
});

describe('at', () => {
  it('reads inside the array and throws outside it', () => {
    expect(at([4, 5, 6], 2)).toBe(6);
    expect(() => at([4, 5, 6], 3)).toThrow(RangeError);
    expect(() => at([], 0)).toThrow(RangeError);
  });
});
