// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT

import { allocate, type LensParams } from './allocate.js';
import { collectiveScore } from './indicators.js';
import { resolveSeason, type SeasonInput, type SeasonResult } from './resolveSeason.js';
import type { Basin, LensId, Scheme } from './types.js';

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
 *   {"id": 7, "cmd": "allocate", "lens": ..., "schemes": [...], "allocable": 10, "params": {}}
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
  const g = state.games.get(String(msg.game));
  need(g, 'unknown_game', `no game "${String(msg.game)}"`);
  return g!;
}

function viewOf(g: Game) {
  return {
    season: g.season, seasons: g.deck.length, done: g.season >= g.deck.length,
    stock: g.stock, inflowLossNext: g.inflowLoss, scores: g.scores.slice(), collectiveScore: collectiveScore(g.scores),
  };
}

function run(state: ServeState, msg: Record<string, unknown>): unknown {
  switch (msg.cmd) {
    case 'version':
      return { protocol: PROTOCOL_VERSION, engine: state.engineVersion };
    case 'init': {
      const id = String(msg.game ?? `g${state.games.size + 1}`);
      need(!state.games.has(id), 'game_exists', `game "${id}" already exists`);
      const schemes = msg.schemes as Scheme[]; const basin = msg.basin as Game['basin']; const deck = msg.deck as Card[];
      need(Array.isArray(schemes) && schemes.length >= 3 && schemes.length <= 5, 'bad_input', 'schemes: 3 to 5 required');
      need(basin?.aquifer && basin.pump && basin.inflow, 'bad_input', 'basin needs aquifer, pump and inflow');
      need(Array.isArray(deck) && deck.length > 0 && deck.every(c => CARDS.includes(c)), 'bad_input', 'deck: non-empty list of wet | normal | dry');
      need(msg.scoring, 'bad_input', 'scoring required');
      state.games.set(id, { schemes, basin, scoring: msg.scoring as Scoring, deck, season: 0, stock: basin.aquifer.initial, inflowLoss: 0, scores: [] });
      return { game: id, ...viewOf(state.games.get(id)!) };
    }
    case 'apply': {
      const g = game(state, msg);
      need(g.season < g.deck.length, 'game_over', 'every season has been played');
      const pumps = (msg.pumps as number[] | undefined) ?? g.schemes.map(() => 0);
      need(Array.isArray(pumps) && pumps.length === g.schemes.length, 'bad_input', 'pumps: one value per scheme');
      const card = g.deck[g.season];
      const result: SeasonResult = resolveSeason({
        schemes: g.schemes, basin: g.basin, inflow: g.basin.inflow[card] - g.inflowLoss, stock: g.stock,
        lens: msg.lens as LensId, lensParams: msg.lensParams as LensParams | undefined, pumps, scoring: g.scoring,
      });
      g.season += 1; g.stock = result.stockNext; g.inflowLoss = result.inflowLossNext; g.scores.push(result.triangle.score);
      return { card, result, ...viewOf(g) };
    }
    case 'view':
      return viewOf(game(state, msg));
    case 'close':
      game(state, msg); state.games.delete(String(msg.game));
      return { closed: String(msg.game) };
    case 'resolve':
      return resolveSeason(msg as unknown as SeasonInput);
    case 'allocate':
      return allocate(msg.lens as LensId, msg.schemes as Scheme[], msg.allocable as number, msg.params as LensParams | undefined);
    default:
      throw new Rejection('unknown_command', `unknown cmd "${String(msg.cmd)}"`);
  }
}

/** Handle one NDJSON line. Never throws: engine errors become `rejected`, protocol errors their own code. */
export function handleLine(state: ServeState, line: string): Reply {
  let msg: Record<string, unknown>;
  try { msg = JSON.parse(line); } catch { return { id: null, ok: false, error: { code: 'bad_json', message: 'line is not JSON' } }; }
  if (msg === null || typeof msg !== 'object' || Array.isArray(msg)) return { id: null, ok: false, error: { code: 'bad_json', message: 'line is not a JSON object' } };
  try {
    return { id: msg.id ?? null, ok: true, result: run(state, msg) };
  } catch (e) {
    const code = e instanceof Rejection ? e.code : 'rejected';
    return { id: msg.id ?? null, ok: false, error: { code, message: e instanceof Error ? e.message : String(e) } };
  }
}
