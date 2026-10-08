// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// The pages, the connection and the API against a fake server: a fake WebSocket that replays engine-generated events
// (fixtures from packages/engine-py/scripts/generate_ui_fixture.py) and a fake fetch. No model number is typed here.
import { act, cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { connect, createRoom, deviceHash, joinRoom, roomInfo, tokenStore } from './api';
import { App } from './App';
import opening from './fixtures/opening-public.json';
import { viewOf, type PublicScenario, type RecordEvent } from './room';
import { Season } from './screens/Season';

const events = opening.events as unknown as RecordEvent[];
const scenario = opening.scenario as PublicScenario;

class FakeSocket {
  static last: FakeSocket | null = null;
  sent: string[] = [];
  listeners: Record<string, ((ev: { data?: string }) => void)[]> = {};
  constructor(public url: string) { FakeSocket.last = this; }
  addEventListener(type: string, fn: (ev: { data?: string }) => void) { (this.listeners[type] ??= []).push(fn); }
  send(text: string) { this.sent.push(text); }
  close() { /* closed */ }
  emit(type: string, data?: unknown) { for (const fn of this.listeners[type] ?? []) fn(data === undefined ? {} : { data: JSON.stringify(data) }); }
}

const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

beforeEach(() => {
  vi.stubGlobal('WebSocket', FakeSocket);
  localStorage.clear();
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); history.replaceState(null, '', '/'); });

describe('api', () => {
  it('creates, reads and joins rooms, and reports server error codes', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(ok({ room: 'ABCDE', facilitatorToken: 'f', displayToken: 'd', joinPath: '/join/ABCDE' }))
      .mockResolvedValueOnce(ok({ room: 'ABCDE', freeRoles: ['A'], phase: 'lobby', scenario }))
      .mockResolvedValueOnce(ok({ token: 't', role: 'A' }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { code: 'role_unavailable' } }), { status: 409 }));
    vi.stubGlobal('fetch', fetchMock);
    expect((await createRoom('default-basin')).room).toBe('ABCDE');
    expect((await roomInfo('ABCDE')).freeRoles).toEqual(['A']);
    expect(await joinRoom('ABCDE', 'A', 'h'.repeat(64))).toBe('t');
    await expect(joinRoom('ABCDE', 'A', 'h'.repeat(64))).rejects.toThrow('role_unavailable');
  });
  it('hashes a device identifier and survives unavailable storage', async () => {
    expect(await deviceHash()).toMatch(/^[0-9a-f]{64}$/);
    tokenStore.set('ABCDE', 'tok');
    expect(tokenStore.get('ABCDE')).toBe('tok');
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
    expect(tokenStore.get('ABCDE')).toBeNull();
    expect(() => tokenStore.set('ABCDE', 'x')).not.toThrow();
    vi.restoreAllMocks();
  });
  it('sends the token as the first message, never in the URL', () => {
    const messages: unknown[] = [];
    const s = connect('ABCDE', 'secret-token', m => messages.push(m));
    const ws = FakeSocket.last as FakeSocket;
    expect(ws.url).not.toContain('secret-token');
    ws.emit('open');
    expect(JSON.parse(ws.sent[0] ?? '{}')).toEqual({ token: 'secret-token' });
    ws.emit('message', { type: 'welcome', role: 'A', room: 'ABCDE' });
    s.send({ intent: 'start_season' });
    expect(JSON.parse(ws.sent[1] ?? '{}')).toEqual({ intent: 'start_season' });
    expect(messages).toEqual([{ type: 'welcome', role: 'A', room: 'ABCDE' }]);
    s.close();
  });
});

describe('pages', () => {
  it('a player with a stored token goes straight to the live season and sees the engine climate', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ok({ room: 'ABCDE', freeRoles: [], phase: 'vote', scenario })));
    tokenStore.set('ABCDE', 'tok-A');
    history.replaceState(null, '', '/join/abcde');
    render(<App />);
    await screen.findByText(/Waiting|Connecting/);
    const ws = FakeSocket.last as FakeSocket;
    act(() => {
      ws.emit('message', { type: 'welcome', role: 'A', room: 'ABCDE' });
      ws.emit('message', { type: 'sync', events: events.slice(0, events.findIndex(e => e.type === 'lens.chosen')) });
    });
    expect(await screen.findByText('How do you share it?')).toBeTruthy();
    act(() => ws.emit('message', { type: 'rejected', code: 'not_proposed', message: 'not_proposed: talmud' }));
    expect(screen.getByRole('status').textContent).toContain('not_proposed');
  });
  it('the facilitator opens a room and gets its code, QR and projector link', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(ok({ room: 'ABCDE', facilitatorToken: 'f', displayToken: 'd', joinPath: '/join/ABCDE' }))
      .mockResolvedValue(ok({ room: 'ABCDE', freeRoles: ['A', 'B', 'C'], phase: 'lobby', scenario })));
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: 'Open a room' }));
    expect(await screen.findByRole('heading', { name: 'Room ABCDE' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Open the projector view' }).getAttribute('href')).toBe('/display/ABCDE#d');
  });
  it('the projector page connects with the token from the URL fragment', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ok({ room: 'ABCDE', freeRoles: [], phase: 'lobby', scenario })));
    history.replaceState(null, '', '/display/abcde#display-token');
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Room ABCDE' })).toBeTruthy();
    const ws = FakeSocket.last as FakeSocket;
    act(() => ws.emit('open'));
    expect(JSON.parse(ws.sent[0] ?? '{}')).toEqual({ token: 'display-token' });
  });
});

describe('Season by phase', () => {
  const at = (n: number) => viewOf(events.slice(0, n));
  it('lobby: the facilitator opens season 1; others wait', async () => {
    const onIntent = vi.fn();
    const lobby = at(events.findIndex(e => e.type === 'season.climate'));
    const { unmount } = render(<Season view={lobby} scenario={scenario} role="authority" onIntent={onIntent} />);
    await userEvent.click(screen.getByRole('button', { name: 'Skip it and open season 1' }));
    expect(onIntent).toHaveBeenCalledWith({ intent: 'start_season' });
    await userEvent.click(screen.getByRole('button', { name: 'Start the practice round' }));
    expect(onIntent).toHaveBeenCalledWith({ intent: 'start_tutorial' });
    unmount();
    render(<Season view={lobby} scenario={scenario} role="A" onIntent={onIntent} />);
    expect(screen.getByText(/Waiting for the facilitator/)).toBeTruthy();
  });
  it('after the choice: the facilitator and projector wait while farms decide (S6-S8 are tested in play.test)', () => {
    const chosen = viewOf(events);
    const { unmount } = render(<Season view={chosen} scenario={scenario} role="display" onIntent={() => undefined} />);
    expect(screen.getByText(/Private turns/)).toBeTruthy();
    unmount();
    render(<Season view={chosen} scenario={scenario} role="A" onIntent={() => undefined} />);
    expect(screen.getByText(/Opening your private turn/)).toBeTruthy();
  });
  it('floor vote (ADR 0003): players choose, the facilitator closes', async () => {
    const onIntent = vi.fn();
    const floor = { ...viewOf(events), phase: 'floor_vote' as const };
    const { unmount } = render(<Season view={floor} scenario={scenario} role="A" onIntent={onIntent} />);
    await userEvent.click(screen.getAllByRole('button', { name: 'Choose' })[0] as HTMLElement);
    expect(onIntent).toHaveBeenCalledWith({ intent: 'floor_vote', rule: expect.any(String) });
    unmount();
    render(<Season view={floor} scenario={scenario} role="authority" onIntent={onIntent} />);
    await userEvent.click(screen.getByRole('button', { name: 'Close the vote' }));
    expect(onIntent).toHaveBeenLastCalledWith({ intent: 'close_floor_vote' });
  });
});
