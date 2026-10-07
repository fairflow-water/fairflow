// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// The client's view of a room, read from the events the server sends this device. Every number shown comes from an
// event computed by the engine (ADR 0002); this module only reads fields and tracks which phase the table is in.

export interface PublicScheme { id: string; name: string; seat: number; shape?: string; glyph?: string; crop?: string }
export interface PublicLens { id: string; plainName: string }
export interface PublicScenario { name: string; schemes: PublicScheme[]; lenses: PublicLens[] }

export interface RecordEvent {
  seq: number; t: string; season: number; actor: string; type: string; visibility: string;
  payload: Record<string, unknown>;
}

export interface Preview { lens: string; Q: number[]; shareOfNeed: number[]; floorVoteNeeded: boolean }
export interface Climate { card: string; inflow: number; reserve: number; allocable: number; previews: Preview[] }

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
}

export const emptyView = (): RoomView => ({
  phase: 'lobby', season: 0, climate: null, proposals: [], votes: {}, leaders: [], chosen: null, floorVotes: {},
});

const str = (v: unknown): string => (typeof v === 'string' ? v : '');

/** Fold the received events into what the screens show (the engine's apply_event, for display only). */
export function viewOf(events: readonly RecordEvent[]): RoomView {
  let v = emptyView();
  for (const e of events) {
    const p = e.payload;
    switch (e.type) {
      case 'season.climate':
        v = { ...emptyView(), phase: 'vote', season: e.season, climate: p as unknown as Climate };
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
      case 'season.resolved':
        v = { ...v, phase: 'reveal' };
        break;
      case 'game.ended':
        v = { ...v, phase: 'ended' };
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
