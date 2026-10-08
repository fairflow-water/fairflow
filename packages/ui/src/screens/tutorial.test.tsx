// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// R3 season 0 on screen: labelled as practice, two lenses, free pumping, no actions, and a reveal that leads to season 1.
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import tutorialA from '../fixtures/tutorial-A.json';
import tutorialPublic from '../fixtures/tutorial-public.json';
import { viewOf, type PublicScenario, type RecordEvent } from '../room';
import { Season } from './Season';

afterEach(cleanup);
const scenario = tutorialPublic.scenario as PublicScenario;
const eventsA = tutorialA.events as unknown as RecordEvent[];
const eventsPub = tutorialPublic.events as unknown as RecordEvent[];
const until = (events: RecordEvent[], type: string) => viewOf(events.slice(0, events.findIndex(e => e.type === type) + 1));

describe('season 0, the practice round', () => {
  it('is labelled as practice and offers only its two lenses', () => {
    const vote = until(eventsPub, 'season.climate');
    expect(vote.tutorial).toBe(true);
    render(<Season view={vote} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.getByText('Practice round (not scored)')).toBeTruthy();
    expect(screen.getAllByTestId(/^lens-/).map(el => el.getAttribute('data-testid')).sort()).toEqual(['lens-proportional', 'lens-utilitarian']);
  });
  it('gives a free private turn with no actions', () => {
    const turn = until(eventsA, 'private.opened');
    render(<Season view={turn} scenario={scenario} role="A" onIntent={() => undefined} />);
    expect(turn.privateTurn!.pumpCostPerMm3).toBe(0);
    expect(screen.getByText(/0 points per Mm³/)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Actions: none this season/ })).toBeTruthy();
  });
  it('reveals as practice, keeps the result out of the scored seasons, and leads to season 1', async () => {
    const done = viewOf(eventsPub);
    expect(done.phase).toBe('reveal');
    expect(done.results).toHaveLength(0);
    expect(done.tutorialResult).not.toBeNull();
    const onIntent = vi.fn();
    render(<Season view={done} scenario={scenario} role="authority" onIntent={onIntent} />);
    expect(screen.getByRole('heading', { name: /Practice round: what happened/ })).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Open season 1' }));
    expect(onIntent).toHaveBeenCalledWith({ intent: 'start_season' });
  });
  it('shows the farm its own practice result only', () => {
    render(<Season view={viewOf(eventsA)} scenario={scenario} role="A" onIntent={() => undefined} />);
    expect(screen.getByLabelText(/Your farm/)).toBeTruthy();
    expect(JSON.stringify(eventsPub)).not.toContain('"pumpsBy"');
  });
});

describe('the lobby', () => {
  const joined = (n: number) => viewOf(eventsPub.slice(0, eventsPub.findIndex(e => e.type === 'player.joined' && e.payload['role'] === 'A') + n));
  it('shows who has joined and keeps the game closed until every farm has', () => {
    const one = joined(1);
    expect(one.seated).toContain('A');
    render(<Season view={one} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.getByText(/still to join/)).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Start the practice round' }) as HTMLButtonElement).disabled).toBe(true);
  });
  it('opens once every farm is seated', () => {
    const all = viewOf(eventsPub.slice(0, eventsPub.findIndex(e => e.type === 'season.climate')));
    expect(scenario.schemes.every(x => all.seated.includes(x.id))).toBe(true);
    render(<Season view={all} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.queryByText(/still to join/)).toBeNull();
    expect((screen.getByRole('button', { name: 'Start the practice round' }) as HTMLButtonElement).disabled).toBe(false);
  });
});
