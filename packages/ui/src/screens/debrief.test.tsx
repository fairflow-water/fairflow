// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// S9 and S10 acceptance checks (blueprint §5.2, ADR 0003, ADR 0004) on engine-played debrief fixtures.
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import debriefA from '../fixtures/debrief-A.json';
import debriefPublic from '../fixtures/debrief-public.json';
import totalsPublic from '../fixtures/totals-public.json';
import { viewOf, type PublicScenario, type RecordEvent } from '../room';
import { needleAngle } from './Reveal';
import { Season } from './Season';

afterEach(() => { cleanup(); localStorage.clear(); });
const scenario = debriefPublic.scenario as PublicScenario;
const open = viewOf(debriefPublic.events as unknown as RecordEvent[]);
const totals = viewOf(totalsPublic.events as unknown as RecordEvent[]);
const mineA = viewOf(debriefA.events as unknown as RecordEvent[]);
const rotation = (id: string) => screen.getByTestId(id).getAttribute('transform');
const fmt = (x: number) => (Number.isInteger(x) ? String(x) : x.toFixed(2));
const last = open.results[open.results.length - 1]!;
const sealed = last.sealed!;

describe('S9 debrief, per-player results opened', () => {
  it('has one tab per season and shows the state after season k', async () => {
    render(<Season view={open} scenario={scenario} role="display" onIntent={() => undefined} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(open.results.length);
    await userEvent.click(tabs[0]!);
    const first = open.results[0]!.sealed!;
    expect(screen.getByTestId('season-score').textContent).toBe(fmt(first.triangle.score));
    expect(screen.getByTestId('verdict').textContent).toContain(scenario.lenses.find(l => l.id === first.verdict.satisfied)!.plainName);
  });
  it('the equalisandum moves only the equal-amounts needles', async () => {
    render(<Season view={open} scenario={scenario} role="display" onIntent={() => undefined} />);
    const pj = rotation('used-pj');
    await userEvent.click(screen.getByRole('radio', { name: 'per person' }));
    expect(rotation('used-se')).toBe(`rotate(${needleAngle(sealed.eSE.person)} 100 100)`);
    expect(rotation('ghost-se')).toBe(`rotate(${needleAngle(last.public.asAllocated.eSE.person)} 100 100)`);
    expect(rotation('used-pj')).toBe(pj);
  });
  it('the F toggle moves only F', async () => {
    render(<Season view={open} scenario={scenario} role="display" onIntent={() => undefined} />);
    const score = screen.getByTestId('season-score').textContent;
    expect(screen.getByTestId('f-line').textContent).toContain(fmt(sealed.F.consumed));
    await userEvent.click(screen.getByRole('button', { name: /Per m³ diverted/ }));
    expect(screen.getByTestId('f-line').textContent).toContain(fmt(sealed.F.diverted));
    expect(screen.getByTestId('season-score').textContent).toBe(score);
  });
  it('lists each farm\'s pumping because the table agreed', () => {
    render(<Season view={open} scenario={scenario} role="display" onIntent={() => undefined} />);
    const rows = within(screen.getByRole('table')).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(sealed.roles.length);
    sealed.roles.forEach((role, i) => expect(rows[i]!.textContent).toContain(fmt(sealed.pumpsBy[role]!)));
  });
  it('the welfare slider re-ranks by the engine values and starts at the reference', () => {
    render(<Season view={open} scenario={scenario} role="display" onIntent={() => undefined} />);
    const w = open.debriefWelfare!;
    const season = w.seasons.find(x => x.season === last.season)!;
    const order = (i: number) => [...Object.entries(season.lenses).map(([k, v]) => [k, v[i]!] as const),
      ...(season.used ? [['used', season.used[i]!] as const] : [])].sort((a, b) => b[1] - a[1]).map(([k]) => `rank-${k}`);
    const shown = () => within(screen.getByTestId('ranking')).getAllByRole('listitem').map(li => li.getAttribute('data-testid'));
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe(String(w.start));
    expect(shown()).toEqual(order(w.start));
    fireEvent.change(screen.getByRole('slider'), { target: { value: String(w.gammas.length - 1) } });
    expect(shown()).toEqual(order(w.gammas.length - 1));
  });
});

describe('S9 debrief, totals only', () => {
  it('keeps every as-used value and every farm figure sealed', () => {
    render(<Season view={totals} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(totals.results.every(r => r.sealed === null)).toBe(true);
    expect(screen.getByTestId('sealed-note')).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.queryByTestId('used-pj')).toBeNull();
    expect(screen.queryByTestId('rank-used')).toBeNull();
    expect(JSON.stringify(totalsPublic.events)).not.toContain('pumpsBy');
  });
});

describe('S10 review', () => {
  it('opens for a player, shows saved answers, keeps drafts and sends a new answer', async () => {
    const onIntent = vi.fn();
    render(<Season view={mineA} scenario={scenario} role="A" onIntent={onIntent} code="FIXTR" />);
    await userEvent.click(screen.getByRole('tab', { name: 'Review form' }));
    expect(mineA.review['like.1']).toBeTruthy();
    const boxes = screen.getAllByRole('textbox');
    expect((boxes[0] as HTMLTextAreaElement).value).toBe(mineA.review['like.1']);
    expect(screen.getAllByRole('button', { name: 'Saved' })).toHaveLength(1);
    await userEvent.type(boxes[1]!, 'more water');
    expect(localStorage.getItem('fairflow.review.FIXTR.A')).toContain('more water');
    await userEvent.click(screen.getAllByRole('button', { name: 'Save' })[0]!);
    expect(onIntent).toHaveBeenCalledWith({ intent: 'review_answer', part: 1, item: 'wish.1', value: 'more water' });
  });
  it('is not offered to the projector or the facilitator', () => {
    render(<Season view={open} scenario={scenario} role="authority" onIntent={() => undefined} />);
    expect(screen.queryByRole('tab', { name: 'Review form' })).toBeNull();
  });
});
