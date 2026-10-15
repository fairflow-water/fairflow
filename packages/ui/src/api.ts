// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Talking to the room server. The role token is sent as the first WebSocket message, never in a URL (it would land in
// logs); it is kept in localStorage so a reloaded phone rejoins its role (blueprint §7.1), and storage failures are
// tolerated (private windows, blocked storage).

import type { PublicScenario, ServerMessage } from './room';

export interface RoomInfo {
  room: string; freeRoles: string[]; phase: string; scenario: PublicScenario;
  researchEnabled?: boolean; infoSheetVersion?: string; // ADR 0011
}
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

/** ADR 0011: part 1 (taking part), the research answer (null when not asked) and the information-sheet version read. */
export interface Consent { infoSheetVersion: string; researchConsent: boolean | null }

export async function joinRoom(
  code: string, role: string, deviceHash: string, consent: Consent, linkingCode: string | null = null,
): Promise<{ token: string; warning?: string }> {
  const linking = linkingCode ? { linkingCode } : {}; // R3 (ADR 0016, proposed): only a code made before the session
  const r = await json<{ token: string; warning?: string }>(await fetch(`/rooms/${encodeURIComponent(code)}/join`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ role, deviceHash, participationAcknowledged: true, ...consent, presurveyComplete: false, ...linking }),
  }));
  return r; // a warning: 'duplicate_linking_code' (ADR 0016)
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
  /** ADR 0011: leaving clears this device's role token and its review drafts for the room. */
  leave(room: string, role: string): void {
    try {
      localStorage.removeItem(`fairflow:${room}`);
      localStorage.removeItem(`fairflow.review.${room}.${role}`);
    } catch { /* storage unavailable: nothing was kept */ }
  },
};

const HOSTED = 'fairflow.hosted'; // the rooms this browser opened as facilitator, with their tokens

/** ADR 0012: the facilitator's tokens are kept on the facilitator's device, so a reloaded page, or a game continued on a
 * later day within the server's retention period, can take the room up again. */
export const hostStore = {
  list(): CreatedRoom[] {
    try { return JSON.parse(localStorage.getItem(HOSTED) ?? '[]') as CreatedRoom[]; } catch { return []; }
  },
  add(room: CreatedRoom): void {
    try { localStorage.setItem(HOSTED, JSON.stringify([room, ...hostStore.list().filter(r => r.room !== room.room)])); }
    catch { /* storage unavailable: the room works until this page is closed */ }
  },
  remove(code: string): void {
    try { localStorage.setItem(HOSTED, JSON.stringify(hostStore.list().filter(r => r.room !== code))); }
    catch { /* storage unavailable: nothing was kept */ }
  },
};

export interface RoomSocket { send(intent: Record<string, unknown>): boolean; close(): void }

/** Connection state for the screen: open; lost and retrying; or refused for good (unknown room or token: the room was
 * deleted after the server's retention period, or the server keeps rooms in memory only and restarted; ADR 0012). */
export type LinkStatus = 'open' | 'reconnecting' | 'gone';

const POLICY_VIOLATION = 1008; // RFC 6455 close code the server uses for a bad token, origin or room: do not retry
const RETRY_FIRST_MS = 500; // layout: first retry after a dropped connection
const RETRY_MAX_MS = 8000; // layout: retries back off by doubling up to this interval

/** One room connection that survives a dropped socket (a phone locked or asleep, Wi-Fi lost): it reopens with
 * backoff, at once when the page becomes visible or the browser comes back online, and sends the token first each
 * time; the server then sends a full sync, so nothing is missed. */
export function connect(code: string, token: string, onMessage: (m: ServerMessage) => void,
  onStatus: (s: LinkStatus) => void = () => undefined): RoomSocket {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${scheme}://${location.host}/rooms/${encodeURIComponent(code)}/ws`;
  let ws: WebSocket;
  let stopped = false;
  let attempt = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;

  function open() {
    timer = undefined;
    const socket = new WebSocket(url);
    ws = socket;
    socket.addEventListener('open', () => { attempt = 0; socket.send(JSON.stringify({ token })); onStatus('open'); });
    socket.addEventListener('message', ev => onMessage(JSON.parse(String(ev.data)) as ServerMessage));
    socket.addEventListener('close', ev => {
      if (stopped || socket !== ws) return;
      if (ev.code === POLICY_VIOLATION) { stopped = true; onStatus('gone'); return; }
      onStatus('reconnecting');
      timer = setTimeout(open, Math.min(RETRY_MAX_MS, RETRY_FIRST_MS * 2 ** attempt));
      attempt += 1;
    });
  }
  function wake() {
    if (stopped || document.visibilityState === 'hidden' || timer === undefined) return;
    clearTimeout(timer);
    open();
  }
  document.addEventListener('visibilitychange', wake);
  window.addEventListener('online', wake);
  open();
  return {
    send(intent) {
      if (ws.readyState !== WebSocket.OPEN) return false;
      ws.send(JSON.stringify(intent));
      return true;
    },
    close() {
      stopped = true;
      if (timer !== undefined) clearTimeout(timer);
      document.removeEventListener('visibilitychange', wake);
      window.removeEventListener('online', wake);
      ws.close();
    },
  };
}
