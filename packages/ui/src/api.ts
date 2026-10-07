// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Talking to the room server. The role token is sent as the first WebSocket message, never in a URL (it would land in
// logs); it is kept in localStorage so a reloaded phone rejoins its role (blueprint §7.1), and storage failures are
// tolerated (private windows, blocked storage).

import type { PublicScenario, ServerMessage } from './room';

export interface RoomInfo { room: string; freeRoles: string[]; phase: string; scenario: PublicScenario }
export interface CreatedRoom { room: string; facilitatorToken: string; displayToken: string; joinPath: string }

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { code?: string } };
    throw new Error(body.detail?.code ?? `http_${response.status}`);
  }
  return (await response.json()) as T;
}

export const createRoom = async (scenario: string): Promise<CreatedRoom> =>
  json<CreatedRoom>(await fetch('/rooms', { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ scenario }) }));

export const roomInfo = async (code: string): Promise<RoomInfo> => json<RoomInfo>(await fetch(`/rooms/${encodeURIComponent(code)}`));

export async function joinRoom(code: string, role: string, deviceHash: string): Promise<string> {
  const r = await json<{ token: string }>(await fetch(`/rooms/${encodeURIComponent(code)}/join`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ role, deviceHash, consentGiven: true, presurveyComplete: true }),
  }));
  return r.token;
}

/** A random per-device identifier, hashed (blueprint §6.2: a salted hash, never a device identifier). */
export async function deviceHash(): Promise<string> {
  const bytes = new TextEncoder().encode(crypto.randomUUID());
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

export const tokenStore = {
  get(room: string): string | null {
    try { return localStorage.getItem(`fairflow:${room}`); } catch { return null; }
  },
  set(room: string, token: string): void {
    try { localStorage.setItem(`fairflow:${room}`, token); } catch { /* storage unavailable: the session still works */ }
  },
};

export interface RoomSocket { send(intent: Record<string, unknown>): void; close(): void }

export function connect(code: string, token: string, onMessage: (m: ServerMessage) => void): RoomSocket {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${scheme}://${location.host}/rooms/${encodeURIComponent(code)}/ws`);
  ws.addEventListener('open', () => ws.send(JSON.stringify({ token })));
  ws.addEventListener('message', ev => onMessage(JSON.parse(String(ev.data)) as ServerMessage));
  return { send: intent => ws.send(JSON.stringify(intent)), close: () => ws.close() };
}
