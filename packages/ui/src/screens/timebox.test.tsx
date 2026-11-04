// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// R20 time-box (classroom plan #69): the Authority can end the game after the current season, so a table still playing
// at the end of the session's play time reaches a valid game end and the debrief.
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import gameA from '../fixtures/game-A.json';
import tutorialA from '../fixtures/tutorial-A.json';
import { viewOf, type PublicScenario, type RecordEvent } from '../room';
import { Season } from './Season';

afterEach(() => { cleanup(); vi.useRealTimers(); });
const scenario = gameA.scenario as PublicScenario;
const events = gameA.events as unknown as RecordEvent[]; // a scored game, as scheme A's device received it
const upTo = (type: string, nth = 1) => {
  let seen = 0;
  const i = events.findIndex(e => e.type === type && ++seen === nth);
  return events.slice(0, i + 1);
};
const privateS2 = upTo('private.opened', 2);
const END_LATER = 'End the game after this season';

describe('the time-box (R20)', () => {
  it('is offered only on the Authority\'s device, in a scored season', () => {
    render(<Season view={viewOf(privateS2)} scenario={scenario} role="authority" onIntent={vi.fn()} events={privateS2} />);
    expect(screen.getByRole('button', { name: END_LATER })).toBeTruthy();
    cleanup();
    render(<Season view={viewOf(privateS2)} scenario={scenario} role="A" onIntent={vi.fn()} events={privateS2} />);
    expect(screen.queryByRole('button', { name: END_LATER })).toBeNull();
    cleanup();
    const practice = (tutorialA.events as unknown as RecordEvent[]).filter(e => e.type !== 'tutorial.resolved'); // its private turn
    render(<Season view={viewOf(practice)} scenario={scenario} role="authority" onIntent={vi.fn()} events={practice} />);
    expect(screen.queryByRole('button', { name: END_LATER })).toBeNull();
  });

  it('asks once more, then sends the time-box with the minutes since the game was created', async () => {
    const created = Date.parse(events[0]!.t);
    const minutes = 80; // test input: the session's play time is up
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(created + minutes * 60_000);
    const onIntent = vi.fn();
    render(<Season view={viewOf(privateS2)} scenario={scenario} role="authority" onIntent={onIntent} events={privateS2} />);
    await userEvent.click(screen.getByRole('button', { name: END_LATER }));
    expect(onIntent).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Yes, end after this season' }));
    expect(onIntent).toHaveBeenCalledExactlyOnceWith({ intent: 'timebox', sessionMinute: minutes });
  });

  it('can be called off before it is sent', async () => {
    const onIntent = vi.fn();
    render(<Season view={viewOf(privateS2)} scenario={scenario} role="authority" onIntent={onIntent} events={privateS2} />);
    await userEvent.click(screen.getByRole('button', { name: END_LATER }));
    await userEvent.click(screen.getByRole('button', { name: 'Keep playing' }));
    expect(onIntent).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: END_LATER })).toBeTruthy();
  });

  it('between seasons (the reveal) it ends the game at once, and says so', async () => {
    const reveal = upTo('season.resolved', 2);
    const onIntent = vi.fn();
    render(<Season view={viewOf(reveal)} scenario={scenario} role="authority" onIntent={onIntent} events={reveal} />);
    expect(screen.queryByRole('button', { name: END_LATER })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'End the game here' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, end the game now' }));
    expect(onIntent).toHaveBeenCalledExactlyOnceWith({ intent: 'timebox', sessionMinute: expect.any(Number) as number });
  });

  it('once sent, every device is told the game ends after this season, and the button is gone', () => {
    const timeboxed: RecordEvent = {
      seq: privateS2.length + 1, t: privateS2[privateS2.length - 1]!.t, season: 2, actor: 'authority',
      type: 'game.timeboxed', visibility: 'public', payload: { atSeason: 2, sessionMinute: 80 }, // test input
    };
    const after = [...privateS2, timeboxed];
    expect(viewOf(after).timeboxed).toBe(true);
    for (const role of ['authority', 'A', 'public']) {
      render(<Season view={viewOf(after)} scenario={scenario} role={role} onIntent={vi.fn()} events={after} />);
      expect(screen.getByText('The game ends after this season.')).toBeTruthy();
      expect(screen.queryByRole('button', { name: END_LATER })).toBeNull();
      cleanup();
    }
  });
});
