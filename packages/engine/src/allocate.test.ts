// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
import { describe, expect, it } from 'vitest';
import { allocate } from './allocate.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };

const schemes = fixtures.schemes;
describe('blueprint §3.1 dry year, AW = 10', () => {
  for (const row of fixtures.dry) {
    if (row.lens === 'utilitarian' || row.lens === 'sufficientarian') continue; // not in the scaffold
    it(row.lens, () => {
      const { Q } = allocate(row.lens as any, schemes as any, 10);
      Q.forEach((q, i) => expect(q).toBeCloseTo(row.Q[i], 2));
    });
  }
});
