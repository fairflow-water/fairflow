// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
import { PassThrough } from 'node:stream';
import { describe, expect, it } from 'vitest';
import { runServe } from './cli.js';
import { createServeState, handleLine, type Reply } from './serve.js';
import fixtures from '../fixtures/default-basin-v1.json' with { type: 'json' };

const { schemes, basin, scoring } = fixtures;
const send = (state: ReturnType<typeof createServeState>, msg: unknown) => handleLine(state, JSON.stringify(msg));
const ok = (r: Reply) => { if (!r.ok) throw new Error(`${r.error.code}: ${r.error.message}`); return r.result as Record<string, any>; };
const err = (r: Reply) => { if (r.ok) throw new Error('expected an error reply'); return r.error.code; };

describe('engine serve (blueprint §7.2), protocol 0', () => {
  it('version', () => {
    expect(ok(send(createServeState('9.9.9'), { id: 1, cmd: 'version' }))).toEqual({ protocol: 0, engine: '9.9.9' });
  });

  it('plays the §3.3 depletion game: dry, dry, normal, each pumps 2', () => {
    const st = createServeState('test');
    expect(ok(send(st, { id: 1, cmd: 'init', game: 'g', schemes, basin, scoring, deck: ['dry', 'dry', 'normal'] }))).toMatchObject({ game: 'g', season: 0, seasons: 3, stock: 20 });
    const stocks: number[] = []; let last: Record<string, any> = {};
    for (let t = 0; t < 3; t++) { last = ok(send(st, { id: 2 + t, cmd: 'apply', game: 'g', lens: 'proportional', pumps: [2, 2, 2] })); stocks.push(last.stock); }
    expect(stocks).toEqual([14, 8, 5]);
    expect(last.result.allocable).toBeCloseTo(17 - 0.2 - 2, 6); // B = 8 after season 2 cuts season 3's inflow by 0.2
    expect(last.done).toBe(true);
    expect(last.scores).toHaveLength(3);
    expect(err(send(st, { id: 9, cmd: 'apply', game: 'g', lens: 'proportional' }))).toBe('game_over');
    expect(ok(send(st, { id: 10, cmd: 'close', game: 'g' }))).toEqual({ closed: 'g' });
    expect(err(send(st, { id: 11, cmd: 'view', game: 'g' }))).toBe('unknown_game');
  });

  it('keeps games apart', () => {
    const st = createServeState('test');
    ok(send(st, { cmd: 'init', game: 'a', schemes, basin, scoring, deck: ['dry'] }));
    ok(send(st, { cmd: 'init', game: 'b', schemes, basin, scoring, deck: ['wet'] }));
    ok(send(st, { cmd: 'apply', game: 'a', lens: 'egalitarian', pumps: [2, 0, 0] }));
    expect(ok(send(st, { cmd: 'view', game: 'a' })).stock).toBe(18);
    expect(ok(send(st, { cmd: 'view', game: 'b' })).stock).toBe(20);
    expect(err(send(st, { cmd: 'init', game: 'a', schemes, basin, scoring, deck: ['dry'] }))).toBe('game_exists');
  });

  it('stateless resolve and allocate', () => {
    const st = createServeState('test');
    const r = ok(send(st, { cmd: 'resolve', schemes, basin, inflow: 12, stock: 20, lens: 'proportional', pumps: [0, 0, 0], scoring }));
    expect(r.ePJ).toBeCloseTo(1, 6);
    expect(ok(send(st, { cmd: 'allocate', lens: 'egalitarian', schemes, allocable: 10 })).Q).toEqual([3.333333, 3.333333, 3.333333]);
  });

  it('answers every bad line with an error and keeps going', () => {
    const st = createServeState('test');
    expect(handleLine(st, 'not json')).toEqual({ id: null, ok: false, error: { code: 'bad_json', message: 'line is not JSON' } });
    expect(err(handleLine(st, '[1, 2]'))).toBe('bad_json');
    expect(err(send(st, { id: 1, cmd: 'fly' }))).toBe('unknown_command');
    expect(err(send(st, { id: 2, cmd: 'init', game: 'x', schemes: schemes.slice(0, 2), basin, scoring, deck: ['dry'] }))).toBe('bad_input');
    expect(err(send(st, { id: 3, cmd: 'init', game: 'x', schemes, basin, scoring, deck: ['drought'] }))).toBe('bad_input');
    ok(send(st, { id: 4, cmd: 'init', game: 'x', schemes, basin, scoring, deck: ['dry'] }));
    expect(err(send(st, { id: 5, cmd: 'apply', game: 'x', lens: 'proportional', pumps: [1] }))).toBe('bad_input');
    expect(err(send(st, { id: 6, cmd: 'apply', game: 'x', lens: 'prioritarian', lensParams: { gamma: 0.5 }, pumps: [0, 0, 0] }))).toBe('rejected');
    expect(err(send(st, { id: 7, cmd: 'apply', game: 'x', lens: 'proportional', pumps: [3, 0, 0] }))).toBe('rejected');
    expect(ok(send(st, { id: 8, cmd: 'view', game: 'x' })).season).toBe(0); // rejected applies leave the game unchanged
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
    const st = createServeState('test'); const n = 2000;
    const line = JSON.stringify({ cmd: 'resolve', schemes, basin, inflow: 12, stock: 20, lens: 'utilitarian', pumps: [1, 2, 0], scoring });
    const t0 = performance.now();
    for (let i = 0; i < n; i++) handleLine(st, line);
    expect((performance.now() - t0) / n).toBeLessThan(10);
  });
});
