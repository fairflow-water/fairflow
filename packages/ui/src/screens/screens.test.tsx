// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// S2–S4 acceptance checks (blueprint §5.2) on engine-generated fixtures; no model number is typed here.
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import opening from '../fixtures/opening-public.json';
import { viewOf, type Climate as ClimateEvent, type PublicScenario, type RecordEvent } from '../room';
import { Climate, sentence } from './Climate';
import { Join } from './Join';
import { LensVote } from './LensVote';

afterEach(cleanup);
const events = opening.events as unknown as RecordEvent[];
const scenario = opening.scenario as PublicScenario;
const voting = viewOf(events.slice(0, events.findIndex(e => e.type === 'lens.chosen')));
const climate = voting.climate as ClimateEvent;

describe('S3 climate', () => {
  it('states the card, inflow, reserve and allocable water from the event', () => {
    render(<Climate climate={climate} scenario={scenario} season={voting.season} />);
    const text = screen.getByRole('heading', { level: 2 }).textContent ?? '';
    expect(text).toBe(sentence(climate));
    for (const value of [climate.inflow, climate.reserve, climate.allocable]) expect(text).toContain(String(value));
  });
  it('draws the river with a width proportional to the inflow', () => {
    const { rerender } = render(<Climate climate={climate} scenario={scenario} season={1} />);
    const w1 = Number(screen.getByTestId('river').getAttribute('width'));
    rerender(<Climate climate={{ ...climate, inflow: climate.inflow * 2 }} scenario={scenario} season={1} />);
    expect(Number(screen.getByTestId('river').getAttribute('width'))).toBeCloseTo(2 * w1, 6);
  });
});

describe('S4 lens vote', () => {
  it('fills every bar to the engine share of need (to 1 %)', () => {
    render(<LensVote view={voting} scenario={scenario} role="display" onIntent={() => undefined} />);
    for (const p of climate.previews) {
      scenario.schemes.forEach((s, i) => {
        const width = parseFloat(screen.getByTestId(`fill-${p.lens}-${s.id}`).style.width);
        expect(Math.abs(width - Math.min(p.shareOfNeed[i] ?? 0, 1) * 100)).toBeLessThanOrEqual(1);
      });
    }
  });
  it('shows the plain name on the front and the academic name only as a subtitle', () => {
    render(<LensVote view={voting} scenario={scenario} role="display" onIntent={() => undefined} />);
    for (const lens of scenario.lenses) {
      const row = screen.getByTestId(`lens-${lens.id}`);
      expect(within(row).getByText(lens.plainName).tagName).toBe('STRONG');
    }
  });
  it('lets a player vote only on proposed lenses, and the facilitator propose and close', async () => {
    const onIntent = vi.fn();
    const player = scenario.schemes[0]?.id ?? '';
    const { unmount } = render(<LensVote view={voting} scenario={scenario} role={player} onIntent={onIntent} />);
    expect(screen.getAllByRole('button').map(b => b.textContent)).toHaveLength(voting.proposals.length);
    await userEvent.click(screen.getAllByRole('button')[0] as HTMLElement);
    expect(onIntent).toHaveBeenCalledWith({ intent: 'vote', lens: expect.any(String) });
    unmount();
    render(<LensVote view={voting} scenario={scenario} role="authority" onIntent={onIntent} />);
    await userEvent.click(screen.getByRole('button', { name: 'Close the vote' }));
    expect(onIntent).toHaveBeenLastCalledWith({ intent: 'close_vote' });
  });
  it('the projector sees no buttons', () => {
    render(<LensVote view={voting} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });
});

describe('S4 Authority veto (R8, ADR 0015)', () => {
  const upTo = events.slice(0, events.findIndex(e => e.type === 'lens.chosen'));
  const target = voting.proposals[0] ?? '';
  const last = upTo[upTo.length - 1]!;
  const vetoed = viewOf([...upTo, { ...last, seq: last.seq + 1, actor: 'authority', type: 'lens.vetoed', payload: { lens: target } }]);
  const plain = (lens: string) => scenario.lenses.find(l => l.id === lens)?.plainName ?? lens;
  it('asks the Authority to confirm, then sends the veto; Cancel sends nothing', async () => {
    const onIntent = vi.fn();
    render(<LensVote view={voting} scenario={scenario} role="authority" onIntent={onIntent} />);
    expect(screen.getAllByRole('button', { name: 'Veto' })).toHaveLength(voting.proposals.length);
    const row = within(screen.getByTestId(`lens-${target}`));
    await userEvent.click(row.getByRole('button', { name: 'Veto' }));
    await userEvent.click(row.getByRole('button', { name: 'Cancel' }));
    expect(onIntent).not.toHaveBeenCalled();
    await userEvent.click(row.getByRole('button', { name: 'Veto' }));
    await userEvent.click(row.getByRole('button', { name: 'Confirm veto' }));
    expect(onIntent).toHaveBeenCalledExactlyOnceWith({ intent: 'veto', lens: target });
  });
  it('after the veto: the lens leaves the ballot, every vote is cleared, the table is told, and no second veto', () => {
    expect(vetoed.proposals).toEqual(voting.proposals.filter(l => l !== target));
    expect(vetoed.votes).toEqual({});
    render(<LensVote view={vetoed} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.getByRole('status').textContent).toBe(`The Authority vetoed ${plain(target)}. Vote again on the remaining lenses.`);
    const row = within(screen.getByTestId(`lens-${target}`));
    expect(row.getByText('Vetoed this season.')).toBeTruthy();
    expect(row.queryByRole('button', { name: 'Propose' })).toBeNull();
    expect(screen.queryAllByRole('button', { name: 'Veto' })).toHaveLength(0);
  });
  it('the veto is spent for the game: the next season offers none', () => {
    const climateEvent = upTo.find(e => e.type === 'season.climate')!;
    const proposals = upTo.filter(e => e.type === 'lens.proposed');
    const veto = { ...last, seq: last.seq + 1, actor: 'authority', type: 'lens.vetoed', payload: { lens: target } };
    const nextSeason = [climateEvent, ...proposals].map((e, k) => ({ ...e, seq: veto.seq + 1 + k, season: climateEvent.season + 1 }));
    const next = viewOf([...upTo, veto, ...nextSeason]);
    expect([next.vetoUsed, next.vetoed, next.proposals.length]).toEqual([true, null, voting.proposals.length]);
    render(<LensVote view={next} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.queryAllByRole('button', { name: 'Veto' })).toHaveLength(0);
    expect(screen.queryByRole('status')).toBeNull();
  });
  it('offers no veto when only one proposal is on the ballot: nothing would be left to re-vote on', () => {
    const single = { ...voting, proposals: voting.proposals.slice(0, 1) };
    render(<LensVote view={single} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.queryAllByRole('button', { name: 'Veto' })).toHaveLength(0);
  });
  it('offers no veto during a tie-break: the Authority breaks the tie instead', () => {
    const tie = { ...voting, phase: 'tiebreak' as const, leaders: voting.proposals };
    render(<LensVote view={tie} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.getAllByRole('button', { name: 'Break the tie' }).length).toBeGreaterThan(0);
    expect(screen.queryAllByRole('button', { name: 'Veto' })).toHaveLength(0);
  });
  it('players and the projector get no veto button, nor does the Authority in the practice round', () => {
    for (const role of [scenario.schemes[0]?.id ?? '', 'display']) {
      const { unmount } = render(<LensVote view={voting} scenario={scenario} role={role} onIntent={() => undefined} />);
      expect(screen.queryAllByRole('button', { name: 'Veto' })).toHaveLength(0);
      unmount();
    }
    render(<LensVote view={{ ...voting, tutorial: true }} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.queryAllByRole('button', { name: 'Veto' })).toHaveLength(0);
  });
});

describe('S2 join (ADR 0011)', () => {
  const room = { room: 'ABCDE', freeRoles: ['A', 'B'], phase: 'lobby', scenario };
  it('course-only: shows no scheme until part 1 is given, asks no research question and no name', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...room, researchEnabled: false }))));
    render(<Join code="ABCDE" onJoined={() => undefined} />);
    await screen.findByText(scenario.name);
    expect(screen.queryByText('Choose your irrigation scheme')).toBeNull();
    expect(screen.getAllByRole('checkbox')).toHaveLength(1); // no pre-session checkbox until the survey exists (D6)
    expect(screen.queryAllByRole('radio')).toHaveLength(0);
    expect(screen.queryByText(/your choice|If you say yes|Changing your mind/)).toBeNull(); // the research sections
    expect(screen.queryByRole('textbox')).toBeNull();
    await userEvent.click(screen.getByRole('checkbox', { name: /will take part/ }));
    expect(screen.getByText('Choose your irrigation scheme')).toBeTruthy();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    vi.unstubAllGlobals();
  });
  it('research enabled: a yes or no is needed, nothing is pre-selected, and the answer is sent', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...room, researchEnabled: true })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ token: 't', role: 'A' })));
    vi.stubGlobal('fetch', fetchMock);
    const onJoined = vi.fn();
    render(<Join code="ABCDE" onJoined={onJoined} />);
    await screen.findByText(scenario.name);
    const [yes, no] = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(yes!.checked || no!.checked).toBe(false);
    await userEvent.click(screen.getByRole('checkbox', { name: /will take part/ }));
    expect(screen.queryByText('Choose your irrigation scheme')).toBeNull();
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    await userEvent.click(screen.getAllByRole('button')[0]!);
    await vi.waitFor(() => expect(onJoined).toHaveBeenCalledWith('t'));
    const body = JSON.parse(String((fetchMock.mock.calls[1] as [string, RequestInit])[1].body)) as Record<string, unknown>;
    expect(body).toMatchObject({ role: 'A', participationAcknowledged: true, researchConsent: false });
    vi.unstubAllGlobals();
  });
});
