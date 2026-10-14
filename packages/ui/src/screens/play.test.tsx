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
import registry from '../../../scenarios/parameters.json';
import { PrivateTurn, UNDO_MS } from './PrivateTurn';
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

describe('timeout marks (ADR 0013)', () => {
  const fixtures = import.meta.glob<{ events: RecordEvent[] }>('../fixtures/*.json', { eager: true, import: 'default' });
  const marked = (events: RecordEvent[]) => events.filter(e => e.type === 'action.played' && 'autoCommitted' in e.payload);
  it('reach no device before a per-player debrief, and every device after it', () => {
    expect(Object.keys(fixtures).length).toBeGreaterThanOrEqual(10); // every stage, as the projector and as A
    for (const [file, data] of Object.entries(fixtures)) {
      const text = JSON.stringify(data.events);
      if (file.includes('/debrief-')) {
        expect(marked(data.events).map(e => e.payload['autoCommittedBy']), file).toEqual(['phone', 'server']);
      } else {
        expect(marked(data.events), file).toEqual([]);
        expect(text.includes('autoCommittedBy'), file).toBe(false);
      }
    }
  });
});

describe('S6 private turn', () => {
  it("shows last season's own results and the engine preview for each pump level", async () => {
    render(<PrivateTurn turn={turn} last={lastMine} demand={lastMine.W} decisionS={null} onCommit={() => true} />);
    expect(screen.getByText(/Last season you used/).textContent).toContain(fmt(lastMine.points));
    for (const option of turn.options) {
      const text = screen.getByTestId('preview').textContent ?? '';
      if (option.points) expect(text).toContain(fmt(option.points['none']!));
      else expect(text).toContain('may run short'); // review E11: no preview above the public limit
      if (option.pumps < turn.cap) await userEvent.click(screen.getByRole('button', { name: 'One more' }));
    }
  });
  it('steps through the offered pump levels up to the cap, which may be fractional (ADR 0008)', async () => {
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={null} onCommit={() => true} />);
    expect((screen.getByRole('button', { name: 'One less' }) as HTMLButtonElement).disabled).toBe(true);
    for (let k = 1; k < turn.options.length; k++) await userEvent.click(screen.getByRole('button', { name: 'One more' }));
    expect(screen.getByTestId('pumps').textContent).toBe(fmt(turn.cap));
    expect(turn.options.at(-1)!.pumps).toBe(turn.cap);
    expect((screen.getByRole('button', { name: 'One more' }) as HTMLButtonElement).disabled).toBe(true);
  });
  it('shows the engine points for a chosen action', async () => {
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={null} onCommit={() => true} />);
    await userEvent.click(screen.getByRole('button', { name: /^Actions:/ }));
    const first = Object.keys(turn.actions)[0]!;
    await userEvent.click(screen.getByRole('radio', { name: new RegExp(first, 'i') }));
    expect(screen.getByTestId('preview').textContent).toContain(fmt(turn.options[0]!.points![first]!));
  });
  it('commits after the undo window, and an undo cancels', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn(() => true);
    render(<PrivateTurn turn={turn} last={null} demand={null} decisionS={null} onCommit={onCommit} />);
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Undo' }).click(); });
    act(() => { vi.advanceTimersByTime(5000); });
    expect(onCommit).not.toHaveBeenCalled();
    act(() => { screen.getByRole('button', { name: 'One more' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(1, null, false); // made by the player, not the timer
  });
  it('auto-commits the current choice when the timer ends, with the 3 s undo toast, marked as the phone timer (R20, ADR 0013)', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn(() => true);
    const opened = { ...turn, openedAt: new Date().toISOString() };
    render(<PrivateTurn turn={opened} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} />);
    act(() => { screen.getByRole('button', { name: 'One more' }).click(); });
    act(() => { vi.advanceTimersByTime(decisionS * 1000 - 500); });
    expect(onCommit).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByText(/Time is up\. Committing your current choice…/)).toBeTruthy();
    expect((screen.getByRole('button', { name: 'One more' }) as HTMLButtonElement).disabled).toBe(true); // the choice is held
    act(() => { vi.advanceTimersByTime(2000); }); // 2.5 s after the deadline
    expect(onCommit).not.toHaveBeenCalled(); // still inside the undo window
    act(() => { vi.advanceTimersByTime(1000); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(turn.options[1]!.pumps, null, true);
  });
  it("the timer's undo window ends inside the server's grace, so the phone's commit always arrives first (ADR 0013)", () => {
    const grace = Number(registry.parameters.find(p => p.key === 'session.privateTurnGraceS')!.default);
    expect(UNDO_MS).toBeLessThan(grace * 1000);
  });
  it('an undo after time is up holds the commit, and the player then commits by hand', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn(() => true);
    const opened = { ...turn, openedAt: new Date().toISOString() };
    render(<PrivateTurn turn={opened} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} />);
    act(() => { vi.advanceTimersByTime(decisionS * 1000 + 500); });
    act(() => { screen.getByRole('button', { name: 'Undo' }).click(); });
    act(() => { vi.advanceTimersByTime(5000); });
    expect(onCommit).not.toHaveBeenCalled(); // the timer does not fire twice; the server's grace remains (ADR 0013)
    act(() => { screen.getByRole('button', { name: 'One more' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(turn.options[1]!.pumps, null, false);
  });
  it('a reconnection (a new clock offset) never skips the undo, fires the timer twice, or relabels a commit by hand', () => {
    vi.useFakeTimers();
    const run = (before: (r: (offset: number) => void, sent: ReturnType<typeof vi.fn>) => void) => {
      const opened = { ...turn, openedAt: new Date().toISOString() }; // each case's turn opens now
      const onCommit = vi.fn(() => true);
      const { rerender, unmount } = render(<PrivateTurn turn={opened} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} clockOffsetMs={0} />);
      const reconnect = (offset: number) => rerender(
        <PrivateTurn turn={opened} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} clockOffsetMs={offset} />);
      before(reconnect, onCommit);
      unmount();
      return onCommit;
    };
    // A: a reconnection inside the timer's undo window: the commit still waits out the window
    const a = run((reconnect, sent) => {
      act(() => { vi.advanceTimersByTime(decisionS * 1000 + 500); });
      act(() => { reconnect(1); });
      expect(screen.getByRole('button', { name: 'Undo' })).toBeTruthy();
      expect(sent).not.toHaveBeenCalled();
      act(() => { vi.advanceTimersByTime(3000); }); // the rest of the window, then it goes out
    });
    expect(a).toHaveBeenCalledExactlyOnceWith(0, null, true);
    // B: undone after time is up, then a reconnection: the timer does not fire again
    const b = run(reconnect => {
      act(() => { vi.advanceTimersByTime(decisionS * 1000 + 500); });
      act(() => { screen.getByRole('button', { name: 'Undo' }).click(); });
      act(() => { reconnect(2); });
      act(() => { vi.advanceTimersByTime(5000); });
    });
    expect(b).not.toHaveBeenCalled();
    // C: a commit by hand in its undo window across the deadline and a reconnection: sent once, as the player's
    const c = run(reconnect => {
      act(() => { vi.advanceTimersByTime(decisionS * 1000 - 1000); });
      act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
      act(() => { vi.advanceTimersByTime(1500); });
      act(() => { reconnect(3); });
      act(() => { vi.advanceTimersByTime(5000); });
    });
    expect(c).toHaveBeenCalledExactlyOnceWith(0, null, false);
    // D: a commit by hand undone after the deadline passed, then a reconnection: the timer does not act late
    const d = run(reconnect => {
      act(() => { vi.advanceTimersByTime(decisionS * 1000 - 1000); });
      act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
      act(() => { vi.advanceTimersByTime(1500); });
      act(() => { screen.getByRole('button', { name: 'Undo' }).click(); });
      act(() => { reconnect(4); });
      act(() => { vi.advanceTimersByTime(5000); });
    });
    expect(d).not.toHaveBeenCalled(); // the server commits the default at its deadline (ADR 0013)
  });
  it("a commit by hand still in its undo window when the timer ends is sent once, as the player's", () => {
    vi.useFakeTimers();
    const onCommit = vi.fn(() => true);
    const opened = { ...turn, openedAt: new Date().toISOString() };
    render(<PrivateTurn turn={opened} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} />);
    act(() => { vi.advanceTimersByTime(decisionS * 1000 - 1000); });
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { vi.advanceTimersByTime(10_000); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(0, null, false);
  });
  it('counts down to the server deadline on the server clock, so a reload does not restart it (ADR 0013)', () => {
    vi.useFakeTimers();
    const elapsedS = 20; // test input: the private turn opened this long ago on the server
    const offsetMs = 5000; // test input: the server's clock runs this far ahead of the phone's
    const openedAt = new Date(Date.now() + offsetMs - elapsedS * 1000).toISOString();
    const props = { turn: { ...turn, openedAt }, last: null, demand: null, decisionS, onCommit: vi.fn() };
    const { unmount } = render(<PrivateTurn {...props} clockOffsetMs={offsetMs} />);
    expect(screen.getByText(`${decisionS - elapsedS} s`)).toBeTruthy();
    unmount();
    act(() => { vi.advanceTimersByTime(3000); }); // the page reloads
    render(<PrivateTurn {...props} clockOffsetMs={offsetMs} />);
    expect(screen.getByText(`${decisionS - elapsedS - 3} s`)).toBeTruthy();
    expect(props.onCommit).not.toHaveBeenCalled();
  });
  it('takes the timer start from the record time of private.opened', () => {
    const opened = eventsA.filter(e => e.type === 'private.opened')[1]!;
    expect(privateS2.privateTurn!.openedAt).toBe(opened.t);
  });
  it('sends a timer commit with autoCommitted and a player commit without it', () => {
    vi.useFakeTimers();
    const onIntent = vi.fn();
    render(<Season view={privateS2} scenario={scenario} role="A" onIntent={onIntent} />); // the fixture turn opened long ago
    expect(onIntent).toHaveBeenCalledExactlyOnceWith({ intent: 'commit', pumps: 0, action: null, autoCommitted: true });
    cleanup();
    const later = { ...privateS2, privateTurn: { ...turn, openedAt: new Date().toISOString() } };
    const byHand = vi.fn();
    render(<Season view={later} scenario={scenario} role="A" onIntent={byHand} />);
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { vi.advanceTimersByTime(3000); });
    expect(byHand).toHaveBeenCalledExactlyOnceWith({ intent: 'commit', pumps: 0, action: null });
  });
  it('commits at once when it opens after the deadline has passed', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn();
    const openedAt = new Date(Date.now() - (decisionS + 1) * 1000).toISOString();
    render(<PrivateTurn turn={{ ...turn, openedAt }} last={null} demand={null} decisionS={decisionS} onCommit={onCommit} />);
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(0, null, true);
  });
  it('keeps a commit that could not be sent and sends it again after the next sync', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn().mockReturnValueOnce(false).mockReturnValue(true);
    const props = { turn, last: null, demand: null, decisionS: null, onCommit };
    const { rerender } = render(<PrivateTurn {...props} resync={1} />);
    act(() => { screen.getByRole('button', { name: 'One more' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Commit my turn' }).click(); });
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(1, null, false);
    expect(screen.getByText(/Not connected. Your turn is kept/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Commit my turn' })).toBeNull(); // the choice is final on this phone
    expect((screen.getByRole('button', { name: 'One more' }) as HTMLButtonElement).disabled).toBe(true);
    rerender(<PrivateTurn {...props} resync={2} />);
    expect(onCommit).toHaveBeenCalledTimes(2);
    expect(onCommit).toHaveBeenLastCalledWith(1, null, false);
    expect(screen.getByText('Sending your turn…')).toBeTruthy();
    expect(screen.queryByText(/Not connected/)).toBeNull();
  });
  it('sends a commit again after a sync even if it went out, since the connection may have died with it', () => {
    vi.useFakeTimers();
    const onCommit = vi.fn(() => true);
    const opened = { ...turn, openedAt: new Date().toISOString() }; // ADR 0013: the turn opens now, so the timer runs its full time
    const props = { turn: opened, last: null, demand: null, decisionS, onCommit };
    const { rerender } = render(<PrivateTurn {...props} resync={1} />);
    rerender(<PrivateTurn {...props} resync={2} />);
    expect(onCommit).not.toHaveBeenCalled(); // no commit made yet: a sync sends nothing
    act(() => { vi.advanceTimersByTime(decisionS * 1000 + 500 + 3000); }); // the deadline, then the 3 s undo (R20)
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(0, null, true);
    rerender(<PrivateTurn {...props} resync={3} />);
    expect(onCommit).toHaveBeenCalledTimes(2);
    expect(onCommit).toHaveBeenLastCalledWith(0, null, true); // the timer's mark goes out again with it
  });
  it('is shown only to a scheme that has not committed; the projector waits', () => {
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
    expect(text).toContain(`about ${fmt(result.pumpsTotalObserved)} Mm³`); // ADR 0004: to the tank's resolution
    expect(Number.isInteger(result.pumpsTotalObserved)).toBe(true);
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
  it('the projector sees no per-scheme result; a scheme sees only its own', () => {
    const { unmount } = render(<Season view={reveal} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(screen.queryByLabelText(/Your scheme/)).toBeNull();
    unmount();
    render(<Season view={upTo(eventsA, 'season.resolved', 1)} scenario={scenario} role="A" onIntent={() => undefined} />);
    expect(screen.getByLabelText(/Your scheme/)).toBeTruthy();
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
    expect(screen.getByTestId(`scheme-${scenario.schemes[0]!.id}`).textContent).toContain(next.mapBands![0]!);
    expect(screen.getByTestId('aquifer').textContent).toContain(String(next.aquifer));
  });
});

describe('S8 game end', () => {
  const endA = viewOf(eventsA);
  const endPub = viewOf(eventsPub);
  it("shows the length, the collective score and this scheme's own goal", () => {
    render(<Season view={endA} scenario={scenario} role="A" onIntent={() => undefined} />);
    const text = screen.getByRole('region').textContent ?? '';
    expect(text).toContain(`${endA.ended!.seasonsPlayed} seasons`);
    expect(screen.getByTestId('score').textContent).toBe(`${Math.round(endA.ended!.collectiveScore * 100)} %`);
    expect(text).toContain(endA.myGoal!.met ? 'met' : 'missed');
    expect(screen.queryByText('Debrief brief')).toBeNull();
  });
  it('the projector sees no scheme goal', () => {
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
  it('names the flag for what it is: below the survival floor, not a failed crop (ADR 0010)', () => {
    render(<GameEnd end={{ ...endPub.ended!, cropFailureFlag: true }} goal={null} role="display" lenses={scenario.lenses} debriefOpened={false} onIntent={() => undefined} />);
    expect(screen.getByText(/below the survival floor two years running/)).toBeTruthy();
    expect(screen.queryByText(/crop failed/)).toBeNull();
  });
});

describe('debrief brief', () => {
  it('groups consecutive seasons under one lens', () => {
    expect(lensRuns(['a', 'a', 'b', 'a'], x => x.toUpperCase())).toBe('A (seasons 1–2) → B (season 3) → A (season 4)');
    expect(lensRuns([], x => x)).toBe('');
  });
});
