// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// Fixtures are engine output (packages/engine-py/scripts/generate_ui_fixture.py); no model number is typed here.
import { describe, expect, it } from 'vitest';
import opening from './fixtures/opening-public.json';
import { applyMessage, tally, viewOf, type RecordEvent } from './room';

const events = opening.events as unknown as RecordEvent[];

describe('viewOf', () => {
  it('follows the table through lobby, vote and choice', () => {
    expect(viewOf(events.filter(e => e.type === 'player.joined' || e.type === 'game.created')).phase).toBe('lobby');
    const upToVotes = events.slice(0, events.findIndex(e => e.type === 'lens.chosen'));
    const v = viewOf(upToVotes);
    expect(v.phase).toBe('vote');
    expect(v.proposals).toEqual(events.filter(e => e.type === 'lens.proposed').map(e => e.payload['lens']));
    expect(viewOf(events).chosen).toBe(events.find(e => e.type === 'lens.chosen')?.payload['lens']);
    expect(viewOf(events).phase).toBe('private');
  });
  it('counts votes from the public lens.voted events', () => {
    const v = viewOf(events);
    const voted = events.filter(e => e.type === 'lens.voted').map(e => String(e.payload['lens']));
    expect(Object.values(tally(v.votes)).reduce((a, b) => a + b, 0)).toBe(voted.length);
  });
  it('a sync replaces and an update appends', () => {
    expect(applyMessage(events, { type: 'sync', events: [] })).toEqual([]);
    expect(applyMessage([], { type: 'events', events })).toEqual(events);
    expect(applyMessage(events, { type: 'rejected', code: 'x', message: 'y' })).toBe(events);
  });
});
