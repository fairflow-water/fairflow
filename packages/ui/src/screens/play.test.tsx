// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// S6–S8 acceptance checks (blueprint §5.2, ADR 0004) on a full engine-played game; no model number is typed here.
import { act, cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import gameA from '../fixtures/game-A.json';
import gamePublic from '../fixtures/game-public.json';
import { viewOf, type PublicScenario, type RecordEvent } from '../room';
import { GameEnd, lensRuns } from './GameEnd';
import { PrivateTurn } from './PrivateTurn';
import { needleAngle, Reveal } from './Reveal';
import { Season } from './Season';

afterEach(() => { cleanup(); vi.useRealTimers(); });
const scenario = gameA.scenario as PublicScenario;
const eventsA = gameA.events as unknown as RecordEvent[];
const eventsPub = gamePublic.events as unknown as RecordEvent[];
const upTo = (events: RecordEvent[], type: string, nth = 1) => {
  let seen = 0;
  const i = events.findIndex(e => e.type === type && ++seen === nth);
  return viewOf(events.slice(0, i + 1));
};
const privateS2 = upTo(eventsA, 'private.opened', 2);
const turn = privateS2.privateTurn!;
const lastMine = privateS2.results[0]!.mine!;
const fmt = (x: number) => (Number.isInteger(x) ? String(x) : x.toFixed(1));
const decisionS = scenario.session!.decisionS!;

describe('S6 private turn', () => {
  it("shows last season's own results and the engine preview for each pump level", async () => {
    render(<PrivateTurn turn={turn} last={lastMine} demand={lastMine.W} decisionS={null} onCommit={() => undefined} />);
    expect(screen.getByText(/Last season you received/).textContent).toContain(fmt(lastMine.points));
    for (const option of turn.options) {
      expect(screen.getByTestId('preview').textContent).toContain(fmt(option.points['none']!));
      if (option.pumps < turn.cap) await userEvent.click(screen.getByRole('button', { name: 'One more' }));
    }
  });
  it('keeps pumping within 0..cap', async () => {
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={null} onCommit={() => undefined} />);
    expect((screen.getByRole('button', { name: 'One less' }) as HTMLButtonElement).disabled).toBe(true);
    for (let k = 0; k < turn.cap; k++) await userEvent.click(screen.getByRole('button', { name: 'One more' }));
    expect(screen.getByTestId('pumps').textContent).toBe(String(turn.cap));
    expect((screen.getByRole('button', { name: 'One more' }) as HTMLButtonElement).disabled).toBe(true);
  });
  it('shows the engine points for a chosen action', async () => {
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={null} onCommit={() => undefined} />);
    await userEvent.click(screen.getByRole('button', { name: /^Actions:/ }));
    const first = Object.keys(turn.actions)[0]!;
    await userEvent.click(screen.getByRole('radio', { name: new RegExp(first, 'i') }));
    expect(screen.getByTestId('preview').textContent).toContain(fmt(turn.options[0]!.points[first]!));
  });
  it('commits after the undo window, and an undo cancels', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn();
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={null} onCommit={onCommit} />);
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Undo' }).click(); });
    act(() => { vi.advanceTimersByTime(5000); });
    expect(onCommit).not.toHaveBeenCalled();
    act(() => { screen.getByRole('button', { name: 'One more' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(1, null);
  });
  it('auto-commits the current choice when the timer ends (R20)', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn();
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} />);
    act(() => { vi.advanceTimersByTime(decisionS * 1000 + 500); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(0, null);
  });
  it('is shown only to a farm that has not committed; the projector waits', () => {
    const { unmount } = render(<Season view={privateS2} scenario={scenario} role="A" onIntent={() => undefined} />);
    expect(screen.getByRole('heading', { name: 'Your turn' })).toBeTruthy();
    unmount();
    render(<Season view={upTo(eventsPub, 'lens.chosen', 2)} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(screen.queryByRole('heading', { name: 'Your turn' })).toBeNull();
  });
});

describe('S7 reveal', () => {
  const reveal = upTo(eventsPub, 'season.resolved', 1);
  const result = reveal.results[0]!.public;
  it('shows total pumping, the coarse tank and the sustainability band word first', () => {
    render(<Reveal result={result} mine={null} season={1} />);
    const text = screen.getByRole('region').textContent ?? '';
    expect(text).toContain(fmt(result.pumpsTotal));
    expect(text).toContain(fmt(result.observedStockNext));
    expect(text).toContain(result.sustainabilityBand);
  });
  it('puts the needles at the as-allocated equity values with band words', async () => {
    render(<Reveal result={result} mine={null} season={1} />);
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByTestId('needle-pj').getAttribute('transform')).toBe(`rotate(${needleAngle(result.asAllocated.ePJ)} 100 100)`);
    expect(screen.getByTestId('needle-se').getAttribute('transform')).toBe(`rotate(${needleAngle(result.asAllocated.eSE.claimant)} 100 100)`);
    expect(screen.getByRole('region').textContent).toContain(result.bands!.eSE);
  });
  it('says when the aquifer is full (ADR 0006), and only then', () => {
    const { unmount } = render(<Reveal result={{ ...result, aquiferFull: true }} mine={null} season={1} />);
    expect(screen.getByTestId('full')).toBeTruthy();
    unmount();
    render(<Reveal result={{ ...result, aquiferFull: false }} mine={null} season={1} />);
    expect(screen.queryByTestId('full')).toBeNull();
  });
  it('clips the needle to [-1, 1]', () => {
    expect(needleAngle(-5)).toBe(needleAngle(-1));
    expect(needleAngle(5)).toBe(needleAngle(1));
  });
  it('the projector sees no per-farm result; a farm sees only its own', () => {
    const { unmount } = render(<Season view={reveal} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(screen.queryByLabelText(/Your farm/)).toBeNull();
    unmount();
    render(<Season view={upTo(eventsA, 'season.resolved', 1)} scenario={scenario} role="A" onIntent={() => undefined} />);
    expect(screen.getByLabelText(/Your farm/)).toBeTruthy();
  });
  it('lets only the facilitator open the next season', async () => {
    const onIntent = vi.fn();
    render(<Season view={reveal} scenario={scenario} role="authority" onIntent={onIntent} />);
    await userEvent.click(screen.getByRole('button', { name: 'Open the next season' }));
    expect(onIntent).toHaveBeenCalledWith({ intent: 'start_season' });
  });
  it("colours next season's map by the last adequacy bands and shows the coarse tank", () => {
    const next = upTo(eventsPub, 'season.climate', 2);
    render(<Season view={next} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(next.mapBands).not.toBeNull();
    expect(screen.getByTestId(`farm-${scenario.schemes[0]!.id}`).textContent).toContain(next.mapBands![0]!);
    expect(screen.getByTestId('aquifer').textContent).toContain(String(next.aquifer));
  });
});

describe('S8 game end', () => {
  const endA = viewOf(eventsA);
  const endPub = viewOf(eventsPub);
  it("shows the length, the collective score and this farm's own goal", () => {
    render(<Season view={endA} scenario={scenario} role="A" onIntent={() => undefined} />);
    const text = screen.getByRole('region').textContent ?? '';
    expect(text).toContain(`${endA.ended!.seasonsPlayed} seasons`);
    expect(screen.getByTestId('score').textContent).toBe(`${Math.round(endA.ended!.collectiveScore * 100)} %`);
    expect(text).toContain(endA.myGoal!.met ? 'met' : 'missed');
    expect(screen.queryByText('Debrief brief')).toBeNull();
  });
  it('the projector sees no farm goal', () => {
    render(<Season view={endPub} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(endPub.myGoal).toBeNull();
    expect(screen.queryByText(/Your goal/)).toBeNull();
  });
  it('gives the facilitator the brief, the safety norm and both debrief choices', async () => {
    const onIntent = vi.fn();
    render(<GameEnd end={endPub.ended!} goal={null} role="authority" lenses={scenario.lenses} debriefOpened={false} onIntent={onIntent} />);
    expect(screen.getByText(/we debrief the rules, not the person/)).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: /reveal who pumped/ }));
    expect(onIntent).toHaveBeenLastCalledWith({ intent: 'open_debrief', perPlayer: true });
    await userEvent.click(screen.getByRole('button', { name: /totals only/ }));
    expect(onIntent).toHaveBeenLastCalledWith({ intent: 'open_debrief', perPlayer: false });
  });
});

describe('debrief brief', () => {
  it('groups consecutive seasons under one lens', () => {
    expect(lensRuns(['a', 'a', 'b', 'a'], x => x.toUpperCase())).toBe('A (seasons 1–2) → B (season 3) → A (season 4)');
    expect(lensRuns([], x => x)).toBe('');
  });
});
