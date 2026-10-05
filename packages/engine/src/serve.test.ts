// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
//
// `engine serve` must give exactly what the engine gives when called directly; no expected model number is written here.

import { PassThrough } from 'node:stream';
import { describe, expect, it } from 'vitest';
import { runServe } from './cli.js';
import { lensParams, scoring as registryScoring } from './registry.testutil.js';
import { resolveSeason } from './resolveSeason.js';
import { createServeState, handleLine, type Reply } from './serve.js';
import type { Basin, Scheme } from './types.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };

const schemes = fixtures.schemes as Scheme[];
const basin = fixtures.basin as Basin & { inflow: Record<'wet' | 'normal' | 'dry', number> };
const scoring = registryScoring();
const cap = basin.pump.cap;
const send = (state: ReturnType<typeof createServeState>, msg: unknown) => handleLine(state, JSON.stringify(msg));
const ok = (r: Reply) => { if (!r.ok) throw new Error(`${r.error.code}: ${r.error.message}`); return r.result as Record<string, any>; };
const err = (r: Reply) => { if (r.ok) throw new Error('expected an error reply'); return r.error.code; };

describe('engine serve (blueprint §7.2), protocol 0', () => {
  it('version', () => {
    expect(ok(send(createServeState('9.9.9'), { id: 1, cmd: 'version' }))).toEqual({ protocol: 0, engine: '9.9.9' });
  });

  it('a served game equals direct resolveSeason calls, season by season, with aquifer and coupling carried over', () => {
    const st = createServeState('test');
    const deck = ['dry', 'dry', 'normal'] as const;
    const params = lensParams('proportional');
    ok(send(st, { cmd: 'init', game: 'g', schemes, basin, scoring, deck }));
    let stock = basin.aquifer.initial; let loss = 0;
    for (const card of deck) {
      const pumps = schemes.map(() => cap);
      const served = ok(send(st, { cmd: 'apply', game: 'g', lens: 'proportional', lensParams: params, pumps }));
      const direct = resolveSeason({ schemes, basin, inflow: basin.inflow[card] - loss, stock, lens: 'proportional', lensParams: params, pumps, scoring });
      expect(served.result).toEqual(direct);
      expect(served.stock).toBe(direct.stockNext);
      stock = direct.stockNext; loss = direct.inflowLossNext;
    }
    const end = ok(send(st, { cmd: 'view', game: 'g' }));
    expect(end.done).toBe(true);
    expect(end.scores).toHaveLength(deck.length);
    expect(err(send(st, { cmd: 'apply', game: 'g', lens: 'proportional', lensParams: params }))).toBe('game_over');
    expect(ok(send(st, { cmd: 'close', game: 'g' }))).toEqual({ closed: 'g' });
    expect(err(send(st, { cmd: 'view', game: 'g' }))).toBe('unknown_game');
  });

  it('keeps games apart', () => {
    const st = createServeState('test');
    ok(send(st, { cmd: 'init', game: 'a', schemes, basin, scoring, deck: ['dry'] }));
    ok(send(st, { cmd: 'init', game: 'b', schemes, basin, scoring, deck: ['wet'] }));
    const a = ok(send(st, { cmd: 'apply', game: 'a', lens: 'egalitarian', lensParams: lensParams('egalitarian'), pumps: [cap, 0, 0] }));
    expect(ok(send(st, { cmd: 'view', game: 'a' })).stock).toBe(a.result.stockNext);
    expect(ok(send(st, { cmd: 'view', game: 'b' })).stock).toBe(basin.aquifer.initial);
    expect(err(send(st, { cmd: 'init', game: 'a', schemes, basin, scoring, deck: ['dry'] }))).toBe('game_exists');
  });

  it('answers every bad line with an error and keeps going; rejected applies leave the game unchanged', () => {
    const st = createServeState('test');
    expect(err(handleLine(st, 'not json'))).toBe('bad_json');
    expect(err(handleLine(st, '[1, 2]'))).toBe('bad_json');
    expect(err(send(st, { cmd: 'fly' }))).toBe('unknown_command');
    expect(err(send(st, { cmd: 'init', game: 'x', schemes: schemes.slice(0, 2), basin, scoring, deck: ['dry'] }))).toBe('bad_input');
    expect(err(send(st, { cmd: 'init', game: 'x', schemes, basin, scoring, deck: ['drought'] }))).toBe('bad_input');
    ok(send(st, { cmd: 'init', game: 'x', schemes, basin, scoring, deck: ['dry'] }));
    expect(err(send(st, { cmd: 'apply', game: 'x', lens: 'proportional', lensParams: {}, pumps: [0] }))).toBe('bad_input');
    expect(err(send(st, { cmd: 'apply', game: 'x', lens: 'prioritarian', lensParams: { weight: '1' }, pumps: [0, 0, 0] }))).toBe('rejected');
    expect(err(send(st, { cmd: 'apply', game: 'x', lens: 'proportional', lensParams: {}, pumps: [cap + 1, 0, 0] }))).toBe('rejected');
    expect(ok(send(st, { cmd: 'view', game: 'x' })).season).toBe(0);
  });

  it('runServe: one reply line per non-empty input line, in order, with ids echoed', async () => {
    const input = new PassThrough(); const output = new PassThrough(); let text = '';
    output.on('data', (c: Buffer) => { text += c.toString(); });
    const done = runServe(input, output, 'test');
    input.end(['{"id":"a","cmd":"version"}', '', 'oops', '{"id":7,"cmd":"view","game":"none"}'].join('\n') + '\n');
    await done;
    const replies = text.trim().split('\n').map(l => JSON.parse(l));
    expect(replies.map(r => [r.id, r.ok])).toEqual([['a', true], [null, false], [7, false]]);
  });

  it('meets the §7.4 budget: a season resolves in < 10 ms in serve', () => {
    const st = createServeState('test'); const n = 2000; const budgetMs = 10;
    const line = JSON.stringify({ cmd: 'resolve', schemes, basin, inflow: basin.inflow.dry, stock: basin.aquifer.initial,
      lens: 'utilitarian', lensParams: {}, pumps: [0, cap, 0], scoring });
    const t0 = performance.now();
    for (let i = 0; i < n; i++) handleLine(st, line);
    expect((performance.now() - t0) / n).toBeLessThan(budgetMs);
  });
});
