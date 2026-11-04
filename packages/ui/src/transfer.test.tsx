// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0018 decision 2, issue #9, on screen: the Authority's device makes a one-time link (shown as a QR code) that moves
// a role to another phone; the new phone opens /transfer/{code}#link, claims it and plays the role; the old phone is
// told the role has moved and stops reconnecting. The link sits in the URL fragment, which browsers never send.
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { claimTransfer, connect, hostStore, offerTransfer, tokenStore } from './api';
import { App } from './App';
import opening from './fixtures/opening-public.json';

const scenario = opening.scenario;
const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

class FakeSocket {
  static OPEN = 1;
  static last: FakeSocket | null = null;
  readyState = 0;
  listeners: Record<string, ((ev: { data?: string; code?: number }) => void)[]> = {};
  constructor(public url: string) { FakeSocket.last = this; }
  addEventListener(type: string, fn: (ev: { data?: string; code?: number }) => void) { (this.listeners[type] ??= []).push(fn); }
  send() { /* the token */ }
  close() { /* closed */ }
  drop(code: number) { for (const fn of this.listeners['close'] ?? []) fn({ code }); }
}

beforeEach(() => { vi.stubGlobal('WebSocket', FakeSocket); localStorage.clear(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); history.replaceState(null, '', '/'); });

describe('moving a role (ADR 0018, #9)', () => {
  it('the API asks for a link with the Authority token and claims it with the new phone\'s device hash', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(ok({ link: 'L1', role: 'A' }))
      .mockResolvedValueOnce(ok({ token: 'T2', role: 'A' }));
    vi.stubGlobal('fetch', fetchMock);
    expect(await offerTransfer('ABCDE', 'auth-token', 'A')).toBe('L1');
    expect(await claimTransfer('ABCDE', 'L1', 'device-hash-0123')).toEqual({ token: 'T2', role: 'A' });
    const [first, second] = fetchMock.mock.calls as unknown as [[string, RequestInit], [string, RequestInit]];
    expect(first[0]).toBe('/rooms/ABCDE/transfers');
    expect(JSON.parse(String(first[1].body))).toEqual({ token: 'auth-token', role: 'A' });
    expect(second[0]).toBe('/rooms/ABCDE/transfers/claim');
    expect(JSON.parse(String(second[1].body))).toEqual({ link: 'L1', deviceHash: 'device-hash-0123' });
  });

  it('the old phone is told the role has moved, and does not reconnect', () => {
    vi.useFakeTimers();
    const status: string[] = [];
    connect('ABCDE', 'old', () => undefined, s => status.push(s));
    const first = FakeSocket.last;
    FakeSocket.last!.drop(4001); // ROLE_MOVED, from the server
    vi.runAllTimers();
    expect(status).toEqual(['moved']);
    expect(FakeSocket.last).toBe(first);
    vi.useRealTimers();
  });

  it('the Authority\'s page shows a one-time QR link for a role', async () => {
    hostStore.add({ room: 'ABCDE', facilitatorToken: 'auth-token', displayToken: 'disp', joinPath: '/join/ABCDE' });
    const fetchMock = vi.fn((url: string) => Promise.resolve(url.endsWith('/transfers')
      ? ok({ link: 'LINK-1', role: 'A' })
      : ok({ room: 'ABCDE', freeRoles: [], phase: 'lobby', scenario })));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    await userEvent.click(await screen.findByRole('button', { name: 'Continue room ABCDE' }));
    await userEvent.click(await screen.findByText('Move a role to another phone'));
    const scheme = scenario.schemes[0]!;
    await userEvent.click(screen.getByRole('button', { name: `Move ${scheme.name}` }));
    const qr = await screen.findByText(`${location.origin}/transfer/ABCDE#LINK-1`);
    expect(qr).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Pass the Authority role' })).toBeTruthy();
  });

  it('the new phone claims the link, keeps the role token, and leaves the link out of the address', async () => {
    history.replaceState(null, '', '/transfer/ABCDE#LINK-1');
    const fetchMock = vi.fn((url: string) => Promise.resolve(url.endsWith('/claim')
      ? ok({ token: 'NEW', role: 'A' })
      : ok({ room: 'ABCDE', freeRoles: [], phase: 'lobby', scenario })));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    await waitFor(() => expect(tokenStore.get('ABCDE')).toBe('NEW'));
    expect(location.pathname).toBe('/join/ABCDE');
    expect(location.hash).toBe('');
  });

  it('a claimed Authority role is kept as a hosted room on the new device', async () => {
    history.replaceState(null, '', '/transfer/ABCDE#LINK-2');
    vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(url.endsWith('/claim')
      ? ok({ token: 'NEW-AUTH', role: 'authority' })
      : ok({ room: 'ABCDE', freeRoles: [], phase: 'lobby', scenario }))));
    render(<App />);
    await waitFor(() => expect(hostStore.list()[0]?.facilitatorToken).toBe('NEW-AUTH'));
    expect(location.pathname).toBe('/');
  });

  it('claims a link once even when the page mounts twice (React StrictMode in development)', async () => {
    history.replaceState(null, '', '/transfer/ABCDE#ONCE');
    const fetchMock = vi.fn((url: string) => Promise.resolve(url.endsWith('/claim')
      ? ok({ token: 'ONCE-TOKEN', role: 'A' })
      : ok({ room: 'ABCDE', freeRoles: [], phase: 'lobby', scenario })));
    vi.stubGlobal('fetch', fetchMock);
    render(<StrictMode><App /></StrictMode>);
    await waitFor(() => expect(tokenStore.get('ABCDE')).toBe('ONCE-TOKEN'));
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/claim'))).toHaveLength(1);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('a used or replaced link says so', async () => {
    history.replaceState(null, '', '/transfer/ABCDE#OLD');
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(
      JSON.stringify({ detail: { code: 'unknown_transfer' } }), { status: 409 }))));
    render(<App />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/link has been used or replaced/)).toBeTruthy();
  });
});
