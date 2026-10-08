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

describe('S2 join', () => {
  it('shows no role until consent is given, and asks for no name', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ room: 'ABCDE', freeRoles: ['A', 'B'], phase: 'lobby', scenario }))));
    render(<Join code="ABCDE" onJoined={() => undefined} />);
    await screen.findByText(scenario.name);
    expect(screen.queryByText('Choose your farm')).toBeNull();
    expect(screen.getAllByRole('checkbox')).toHaveLength(1); // no pre-session checkbox until the survey exists (D6)
    expect(screen.queryByRole('textbox')).toBeNull();
    await userEvent.click(screen.getByRole('checkbox', { name: /agree to take part/ }));
    expect(screen.getByText('Choose your farm')).toBeTruthy();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    vi.unstubAllGlobals();
  });
});
