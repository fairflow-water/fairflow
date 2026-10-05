// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import { allocate } from './allocate.js';
import { collectiveScore } from './indicators.js';
import { resolveSeason, type SeasonInput, type SeasonResult } from './resolveSeason.js';
import type { Basin, Scheme } from './types.js';
import * as v from './validate.js';

/**
 * Blueprint §7.2 — `engine serve`: NDJSON commands in, one NDJSON result per command out, many games per process.
 *
 * Protocol 0 (until the Season Record and applyEvent exist, when `apply` will take events instead of decisions):
 *   {"id": 1, "cmd": "version"}
 *   {"id": 2, "cmd": "init", "game": "g1", "schemes": [...], "basin": {...}, "scoring": {...}, "deck": ["normal", "dry", ...]}
 *   {"id": 3, "cmd": "apply", "game": "g1", "lens": "proportional", "lensParams": {}, "pumps": [0, 2, 0]}
 *   {"id": 4, "cmd": "view", "game": "g1"}
 *   {"id": 5, "cmd": "close", "game": "g1"}
 *   {"id": 6, "cmd": "resolve", ...SeasonInput}            stateless, one season
 *   {"id": 7, "cmd": "allocate", "lens": ..., "schemes": [...], "allocable": 10, "params": {...}, "survivalFloor": ...}
 * Every reply is {"id", "ok": true, "result"} or {"id", "ok": false, "error": {"code", "message"}}; a bad command never
 * stops the process. `basin.inflow` holds the absolute inflow per card (§2.2). The deck is the caller's: the sealed,
 * committed deck of a real game belongs to the record (week 2), and the balance harness draws its own.
 */
export const PROTOCOL_VERSION = 0;

type Card = 'wet' | 'normal' | 'dry';
type Scoring = SeasonInput['scoring'];
interface Game {
  schemes: Scheme[]; basin: Basin & { inflow: Record<Card, number> }; scoring: Scoring; deck: Card[];
  season: number; stock: number; inflowLoss: number; scores: number[];
}
export interface ServeState { games: Map<string, Game>; engineVersion: string }
export type Reply = { id: unknown; ok: true; result: unknown } | { id: unknown; ok: false; error: { code: string; message: string } };

export const createServeState = (engineVersion: string): ServeState => ({ games: new Map(), engineVersion });

class Rejection extends Error { constructor(readonly code: string, message: string) { super(message); } }
const need = (cond: unknown, code: string, message: string): void => { if (!cond) throw new Rejection(code, message); };
const CARDS: readonly string[] = ['wet', 'normal', 'dry'];

function game(state: ServeState, msg: Record<string, unknown>): Game {
  const id = v.string(msg['game'], 'game');
  const g = state.games.get(id);
  if (g === undefined) throw new Rejection('unknown_game', `no game "${id}"`);
  return g;
}

function viewOf(g: Game) {
  return {
    season: g.season, seasons: g.deck.length, done: g.season >= g.deck.length,
    stock: g.stock, inflowLossNext: g.inflowLoss, scores: g.scores.slice(), collectiveScore: collectiveScore(g.scores),
  };
}

function card(value: unknown, path: string): Card {
  const c = v.string(value, path);
  if (!CARDS.includes(c)) throw new v.InputError(`${path}: expected wet | normal | dry`);
  return c as Card;
}

function run(state: ServeState, msg: Record<string, unknown>): unknown {
  const cmd = msg['cmd'];
  switch (cmd) {
    case 'version':
      return { protocol: PROTOCOL_VERSION, engine: state.engineVersion };
    case 'init': {
      const id = msg['game'] === undefined ? `g${state.games.size + 1}` : v.string(msg['game'], 'game');
      need(!state.games.has(id), 'game_exists', `game "${id}" already exists`);
      const schemes = v.schemes(msg['schemes'], 'schemes');
      need(schemes.length >= 3 && schemes.length <= 5, 'bad_input', 'schemes: 3 to 5 required'); // §1.2 three to five schemes
      const inflowIn = v.object(v.object(msg['basin'], 'basin')['inflow'], 'basin.inflow');
      const basin = { ...v.basin(msg['basin'], 'basin'),
        inflow: { wet: v.number(inflowIn['wet'], 'basin.inflow.wet'), normal: v.number(inflowIn['normal'], 'basin.inflow.normal'),
          dry: v.number(inflowIn['dry'], 'basin.inflow.dry') } };
      const deck = v.array(msg['deck'], 'deck').map((c, i) => card(c, `deck[${i}]`));
      need(deck.length > 0, 'bad_input', 'deck: at least one card');
      const g: Game = { schemes, basin, scoring: v.scoring(msg['scoring'], 'scoring'), deck, season: 0,
        stock: basin.aquifer.initial, inflowLoss: 0, scores: [] };
      state.games.set(id, g);
      return { game: id, ...viewOf(g) };
    }
    case 'apply': {
      const g = game(state, msg);
      const next = g.deck[g.season];
      if (next === undefined) throw new Rejection('game_over', 'every season has been played');
      const pumps = msg['pumps'] === undefined ? g.schemes.map(() => 0) : v.numbers(msg['pumps'], 'pumps');
      need(pumps.length === g.schemes.length, 'bad_input', 'pumps: one value per scheme');
      const result: SeasonResult = resolveSeason({
        schemes: g.schemes, basin: g.basin, inflow: g.basin.inflow[next] - g.inflowLoss, stock: g.stock,
        lens: v.lensId(msg['lens'], 'lens'), lensParams: v.lensParams(msg['lensParams'], 'lensParams'), pumps, scoring: g.scoring,
      });
      g.season += 1; g.stock = result.stockNext; g.inflowLoss = result.inflowLossNext; g.scores.push(result.triangle.score);
      return { card: next, result, ...viewOf(g) };
    }
    case 'view':
      return viewOf(game(state, msg));
    case 'close': {
      const id = v.string(msg['game'], 'game');
      game(state, msg); state.games.delete(id);
      return { closed: id };
    }
    case 'resolve':
      return resolveSeason(v.seasonInput(msg));
    case 'allocate':
      return allocate(v.lensId(msg['lens'], 'lens'), v.schemes(msg['schemes'], 'schemes'), v.number(msg['allocable'], 'allocable'),
        v.lensParams(msg['params'], 'params'), v.number(msg['survivalFloor'], 'survivalFloor'));
    default:
      throw new Rejection('unknown_command', `unknown cmd "${String(cmd)}"`);
  }
}

/** Handle one NDJSON line. Never throws: engine errors become `rejected`, protocol errors their own code. */
export function handleLine(state: ServeState, line: string): Reply {
  let parsed: unknown;
  try { parsed = JSON.parse(line); } catch { return { id: null, ok: false, error: { code: 'bad_json', message: 'line is not JSON' } }; }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) return { id: null, ok: false, error: { code: 'bad_json', message: 'line is not a JSON object' } };
  const msg = parsed as Record<string, unknown>; // checked just above: a non-null, non-array object
  const id = msg['id'] ?? null;
  try {
    return { id, ok: true, result: run(state, msg) };
  } catch (e) {
    const code = e instanceof Rejection ? e.code : e instanceof v.InputError ? 'bad_input' : 'rejected';
    return { id, ok: false, error: { code, message: e instanceof Error ? e.message : String(e) } };
  }
}
