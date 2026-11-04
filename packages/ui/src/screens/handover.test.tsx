// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0018 decision 2: the facilitator sets, when opening a room, after which season the Authority role passes to
// another student's phone (0 = never; the scenario gives the default). The record carries it in `treatment.assigned`;
// at the reveal of that season the Authority's device asks to pass the role on, with the one-time link as a QR code.
import { act, cleanup, render, renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { treatments, basin } from '../../../scenarios/default-basin.json';
import { App } from '../App';
import gamePublic from '../fixtures/game-public.json';
import { viewOf, type PublicScenario, type RecordEvent } from '../room';
import { useAuthorityLink, type AuthorityLink } from './Handover';
import { Season } from './Season';

const scenario = gamePublic.scenario as PublicScenario;
const events = gamePublic.events as unknown as RecordEvent[]; // a scored game, as the Authority's device received it
const SEASON = treatments.authorityHandoverSeason; // the scenario's hand-over season, which the fixture records
const upTo = (type: string, nth = 1) => {
  let seen = 0;
  const i = events.findIndex(e => e.type === type && ++seen === nth);
  return events.slice(0, i + 1);
};
const PASS = 'Show the code for the next Authority';
const link = (over: Partial<AuthorityLink> = {}): AuthorityLink => ({ url: null, error: null, make: vi.fn(), ...over });

beforeEach(() => { localStorage.clear(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('the hand-over season (ADR 0018)', () => {
  it('the room view reads it from treatment.assigned and keeps it, and notes a hand-over, across seasons', () => {
    expect(viewOf(upTo('season.resolved', SEASON)).handoverSeason).toBe(SEASON);
    const moved = { ...events[0]!, seq: 999, type: 'authority.handover', season: SEASON,
      payload: { season: SEASON, fromDevice: 'a', toDevice: 'b' } } as RecordEvent;
    const after = viewOf([...upTo('season.resolved', SEASON), moved, ...events.filter(e => e.type === 'season.climate').slice(SEASON, SEASON + 1)]);
    expect(after.handoverSeason).toBe(SEASON);
    expect(after.handedOverIn).toBe(SEASON);
  });

  it('at the reveal of that season the Authority is asked to pass the role on, and gets the link as a QR code', async () => {
    const shown = upTo('season.resolved', SEASON);
    const makeLink = vi.fn(() => Promise.resolve('https://table.example/transfer/ABCDE#L1'));
    function Host() { // the host page's wiring: the real hook, handed to the season screen
      const l = useAuthorityLink(makeLink);
      return <Season view={viewOf(shown)} scenario={scenario} role="authority" onIntent={vi.fn()} events={shown} passAuthority={l} />;
    }
    render(<Host />);
    expect(screen.getByRole('heading', { name: 'Pass the Authority role' })).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: PASS }));
    expect(makeLink).toHaveBeenCalledOnce();
    expect(await screen.findByText('https://table.example/transfer/ABCDE#L1')).toBeTruthy();
    expect(await screen.findByRole('img', { name: /QR code/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Open the next season' })).toBeTruthy(); // keeping the role stays possible
  });

  it('is not asked in other seasons, on other devices, once handed over, or when the setting is 0', () => {
    const before = upTo('season.resolved', SEASON - 1);
    const at = upTo('season.resolved', SEASON);
    const ask = (shown: RecordEvent[], role = 'authority') => {
      render(<Season view={viewOf(shown)} scenario={scenario} role={role} onIntent={vi.fn()} events={shown} passAuthority={link()} />);
      const found = screen.queryByRole('heading', { name: 'Pass the Authority role' });
      cleanup();
      return found !== null;
    };
    expect(ask(before)).toBe(false);
    expect(ask(at, 'display')).toBe(false);
    const moved = { ...at[at.length - 1]!, seq: 999, type: 'authority.handover', payload: { season: SEASON, fromDevice: 'a', toDevice: 'b' } } as RecordEvent;
    expect(ask([...at, moved])).toBe(false);
    const never = at.map(e => e.type === 'treatment.assigned' ? { ...e, payload: { ...e.payload, authorityHandoverSeason: 0 } } : e);
    expect(ask(never)).toBe(false);
  });

  it('a move for a broken phone during play, or at an earlier reveal, still leaves the prompt at the hand-over season', () => {
    const at = upTo('season.resolved', SEASON);
    const move = (season: number) => ({ ...at[0]!, seq: 999, type: 'authority.handover', season,
      payload: { season, fromDevice: 'a', toDevice: 'b' } }) as RecordEvent;
    const during = at.findIndex(e => e.type === 'private.opened' && e.season === SEASON);
    const earlier = at.findIndex(e => e.type === 'season.resolved' && e.season === SEASON - 1);
    for (const shown of [
      [...at.slice(0, during + 1), move(SEASON), ...at.slice(during + 1)], // the phone broke during the season's play
      [...at.slice(0, earlier + 1), move(SEASON - 1), ...at.slice(earlier + 1)], // moved at the reveal before it
    ]) {
      render(<Season view={viewOf(shown)} scenario={scenario} role="authority" onIntent={vi.fn()} events={shown} passAuthority={link()} />);
      expect(screen.getByRole('heading', { name: 'Pass the Authority role' })).toBeTruthy();
      cleanup();
    }
  });

  it('the start page sends the chosen season with the new room, the scenario\'s default first', async () => {
    const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() => Promise.resolve(new Response(JSON.stringify({ detail: { code: 'stop' } }), { status: 409 })));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    const choice = screen.getByRole('combobox', { name: /Pass the Authority role to another student/ });
    expect((choice as HTMLSelectElement).value).toBe(String(SEASON));
    const options = [...(choice as HTMLSelectElement).options].map(o => o.value);
    expect(options).toEqual([...Array.from({ length: basin.gameLength.min - 1 }, (_, i) => String(i + 1)), '0']);
    await userEvent.click(screen.getByRole('button', { name: 'Open a room' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(JSON.parse(String(fetchMock.mock.calls[0]![1]!.body))).toEqual({ scenario: 'default-basin', authorityHandoverSeason: SEASON });
    await userEvent.selectOptions(choice, '0');
    await userEvent.click(screen.getByRole('button', { name: 'Open a room' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(String(fetchMock.mock.calls[1]![1]!.body))).toEqual({ scenario: 'default-basin', authorityHandoverSeason: 0 });
  });

  it('keeps one Authority link: a newer one replaces the shown one, and a refusal is said in words', async () => {
    let n = 0;
    const makeLink = vi.fn(() => (++n === 3 ? Promise.reject(new Error('not_authority')) : Promise.resolve(`https://t.example/transfer/ABCDE#L${n}`)));
    const { result } = renderHook(() => useAuthorityLink(makeLink));
    act(() => { result.current.make(); });
    await waitFor(() => expect(result.current.url).toBe('https://t.example/transfer/ABCDE#L1'));
    act(() => { result.current.make(); });
    expect(result.current.url).toBeNull(); // the replaced link leaves the screen at once
    await waitFor(() => expect(result.current.url).toBe('https://t.example/transfer/ABCDE#L2'));
    act(() => { result.current.make(); });
    await waitFor(() => expect(result.current.error).toBe('not_authority'));
    expect(result.current.url).toBeNull();
    const shown = upTo('season.resolved', SEASON);
    render(<Season view={viewOf(shown)} scenario={scenario} role="authority" onIntent={vi.fn()} events={shown}
      passAuthority={link({ error: 'not_authority' })} />);
    expect(screen.getByRole('alert').textContent).toBe('This device no longer holds the Authority role.');
  });

  it('a slow older request never replaces the newer link on screen', async () => {
    const replies: ((v: string) => void)[] = [];
    const fails: ((e: Error) => void)[] = [];
    const makeLink = vi.fn(() => new Promise<string>((ok, fail) => { replies.push(ok); fails.push(fail); }));
    const { result } = renderHook(() => useAuthorityLink(makeLink));
    act(() => { result.current.make(); }); // A
    act(() => { result.current.make(); }); // B, which replaces A on the server
    act(() => { result.current.make(); }); // C, which replaces B
    await act(async () => { replies[2]!('https://t.example/transfer/ABCDE#C'); await Promise.resolve(); });
    await act(async () => { replies[0]!('https://t.example/transfer/ABCDE#A'); await Promise.resolve(); }); // a late success
    await act(async () => { fails[1]!(new Error('late')); await Promise.resolve(); }); // a late refusal
    expect(result.current.url).toBe('https://t.example/transfer/ABCDE#C');
    expect(result.current.error).toBeNull();
  });

  it('says in words when the server refuses the hand-over season', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: { code: 'bad_treatment' } }), { status: 409 }))));
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: 'Open a room' }));
    expect((await screen.findByRole('alert')).textContent).toBe('That hand-over season is outside the game. Choose another and open the room again.');
  });
});
