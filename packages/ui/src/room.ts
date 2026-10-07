// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// The client's view of a room, read from the events the server sends this device. Every number shown comes from an
// event computed by the engine (ADR 0002); this module only reads fields and tracks which phase the table is in.

export interface PublicScheme { id: string; name: string; seat: number; shape?: string; glyph?: string; crop?: string }
export interface PublicLens { id: string; plainName: string }
export interface PublicScenario {
  name: string; schemes: PublicScheme[]; lenses: PublicLens[];
  session?: { decisionS?: number };
}

export interface RecordEvent {
  seq: number; t: string; season: number; actor: string; type: string; visibility: string;
  payload: Record<string, unknown>;
}

export interface Preview { lens: string; Q: number[]; shareOfNeed: number[]; floorVoteNeeded: boolean }
export interface SchemeInForce { id: string; demandMm3: number; capacityT: number; price: number; beta: number; areaHa: number }
export interface Climate {
  card: string; inflow: number; reserve: number; allocable: number; previews: Preview[]; schemes?: SchemeInForce[];
}
export type Band = 'good' | 'fair' | 'ok' | 'poor' | 'warning' | 'unsustainable';
export interface Allocation { lens: string; Q: number[]; adequacyBands?: Band[] }
/** S6: what the engine previewed for this farm alone (a `self` event). */
export interface PrivateTurn {
  role: string; cap: number; pumpCostPerMm3: number; actions: Record<string, number>;
  options: { pumps: number; yieldT: number; points: Record<string, number> }[];
}
export interface Dials { ePJ: number; eSE: { claimant: number; hectare: number; person: number }; F: { consumed: number; diverted: number } }
export interface PublicResult {
  allocable: number; pumpsTotal: number; observedStockNext: number; inflowLossNext: number; asAllocated: Dials;
  sustainabilityBand: Band; bands?: { ePJ: Band; eSE: Band; F: Band };
}
/** This farm's own results for a season (the `self` part of season.resolved). */
export interface MyResult { pumpCost: number; P: number; W: number; A: number; Y: number; dL: number; L: number; cropFailure: boolean }
export interface SeasonResult { season: number; public: PublicResult; mine: MyResult | null }
export interface GameEnd {
  T: number; truncated: boolean; seasonsPlayed: number; collectiveScore: number; cropFailureFlag: boolean;
  brief?: { heaviestPumping: { season: number; pumpsTotal: number } | null; lensBySeason: string[]; lensChanges: number; floorVotes: number };
  authorityGoal?: { maxMeanPumping: number; meanPumping: number; met: boolean };
}
export interface GoalResult { role: string; kind: string; threshold: number; value: number; met: boolean }

export type Phase = 'lobby' | 'vote' | 'tiebreak' | 'floor_vote' | 'private' | 'reveal' | 'ended';

export interface RoomView {
  phase: Phase;
  season: number;
  climate: Climate | null;
  proposals: string[];
  votes: Record<string, string>;
  leaders: string[];
  chosen: string | null;
  floorVotes: Record<string, string>;
  allocation: Allocation | null;
  mapBands: Band[] | null; // last season's public adequacy bands, for the S3 map (outlines in season 1)
  privateTurn: PrivateTurn | null;
  myCommit: { pumps: number; action: string | null } | null;
  results: SeasonResult[];
  aquifer: number | null; // the observed (coarse) tank level the table sees (ADR 0004)
  ended: GameEnd | null;
  myGoal: GoalResult | null;
  debriefOpened: boolean;
}

export const emptyView = (): RoomView => ({
  phase: 'lobby', season: 0, climate: null, proposals: [], votes: {}, leaders: [], chosen: null, floorVotes: {},
  allocation: null, mapBands: null, privateTurn: null, myCommit: null, results: [], aquifer: null, ended: null,
  myGoal: null, debriefOpened: false,
});

const str = (v: unknown): string => (typeof v === 'string' ? v : '');

/** Fold the received events into what the screens show (the engine's apply_event, for display only). */
export function viewOf(events: readonly RecordEvent[]): RoomView {
  let v = emptyView();
  for (const e of events) {
    const p = e.payload;
    switch (e.type) {
      case 'game.created':
        v = { ...v, aquifer: typeof p['aquiferInitial'] === 'number' ? p['aquiferInitial'] : null };
        break;
      case 'season.climate':
        v = {
          ...emptyView(), phase: 'vote', season: e.season, climate: p as unknown as Climate,
          mapBands: v.allocation?.adequacyBands ?? null, results: v.results, aquifer: v.aquifer,
        };
        break;
      case 'allocation.issued':
        v = { ...v, allocation: p as unknown as Allocation };
        break;
      case 'private.opened':
        v = { ...v, privateTurn: p as unknown as PrivateTurn };
        break;
      case 'action.played':
        v = { ...v, myCommit: { pumps: Number(p['pumps']), action: typeof p['action'] === 'string' ? p['action'] : null } };
        break;
      case 'goal.result':
        v = { ...v, myGoal: p as unknown as GoalResult };
        break;
      case 'debrief.opened':
        v = { ...v, debriefOpened: true };
        break;
      case 'lens.proposed':
        v = { ...v, proposals: [...v.proposals, str(p['lens'])] };
        break;
      case 'lens.voted':
        v = { ...v, votes: { ...v.votes, [str(p['voter'])]: str(p['lens']) } };
        break;
      case 'lens.tied':
        v = { ...v, phase: 'tiebreak', leaders: (p['leaders'] as string[] | undefined) ?? [] };
        break;
      case 'lens.chosen':
        v = { ...v, chosen: str(p['lens']), phase: p['floorVoteNeeded'] === true ? 'floor_vote' : 'private' };
        break;
      case 'lens.floorVoted':
        v = { ...v, floorVotes: { ...v.floorVotes, [str(p['voter'])]: str(p['rule']) } };
        break;
      case 'lens.floorRule':
        v = { ...v, phase: 'private' };
        break;
      case 'season.resolved': {
        const pub = p['public'] as PublicResult;
        const mine = (p['self'] as Partial<MyResult> | undefined) ?? {};
        const result: SeasonResult = { season: e.season, public: pub, mine: 'Y' in mine ? (mine as MyResult) : null };
        v = { ...v, phase: 'reveal', results: [...v.results, result], aquifer: pub.observedStockNext };
        break;
      }
      case 'game.ended':
        v = { ...v, phase: 'ended', ended: p as unknown as GameEnd };
        break;
      default:
        break;
    }
  }
  return v;
}

/** Votes per lens, counted from the public lens.voted events (a tally, not a model number). */
export function tally(votes: Record<string, string>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const lens of Object.values(votes)) out[lens] = (out[lens] ?? 0) + 1;
  return out;
}

export type ServerMessage =
  | { type: 'welcome'; role: string; room: string }
  | { type: 'sync' | 'events'; events: RecordEvent[] }
  | { type: 'rejected'; code: string; message: string }
  | { type: 'invalid'; fields: string[] };

/** Merge a server message into the events this device holds: a sync replaces them, an update appends. */
export function applyMessage(events: RecordEvent[], msg: ServerMessage): RecordEvent[] {
  if (msg.type === 'sync') return msg.events;
  if (msg.type === 'events') return [...events, ...msg.events];
  return events;
}
