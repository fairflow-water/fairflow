// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Keeps the screen on for the session, until the room is gone (blueprint §5.4 "timers from timestamps with a Wake Lock
// for the session", §7.3; E7). A locked phone drops its connection and misses its turn's countdown. The browser
// releases the lock whenever the page is hidden, so it is taken again each time the page becomes visible. Where the Screen Wake Lock API is missing
// (iOS before 16.4) or refuses, nothing happens: the blueprint's fallback is the facilitator's reminder (§7.3).
import { useEffect, useState } from 'react';

export type WakeLockState = 'off' | 'held' | 'unsupported' | 'refused';

interface Sentinel { release: () => Promise<void>; addEventListener?: (type: 'release', fn: () => void) => void }
interface WakeLockApi { request: (type: 'screen') => Promise<Sentinel> }

export function useWakeLock(active: boolean): WakeLockState {
  const [state, setState] = useState<WakeLockState>('off');
  useEffect(() => {
    const api = (navigator as Navigator & { wakeLock?: WakeLockApi }).wakeLock;
    if (!active) { setState('off'); return undefined; }
    if (!api) { setState('unsupported'); return undefined; }
    let sentinel: Sentinel | null = null;
    let pending = false; // one request at a time: a second would leave the first's lock with no one to release it
    let stopped = false;
    const take = () => {
      if (stopped || pending || sentinel || document.visibilityState !== 'visible') return;
      pending = true;
      api.request('screen').then(s => {
        pending = false;
        if (stopped) { void s.release(); return; }
        sentinel = s;
        setState('held');
        s.addEventListener?.('release', () => { if (sentinel === s) sentinel = null; if (!stopped) setState('off'); });
      }, () => {
        pending = false;
        if (stopped) return;
        // a page hidden while it asked is refused by the browser; it asks again when visible, so that is not a refusal
        if (document.visibilityState === 'visible') setState('refused'); else setState('off');
      });
    };
    const onVisible = () => { if (document.visibilityState === 'visible') take(); };
    document.addEventListener('visibilitychange', onVisible);
    take();
    return () => {
      stopped = true;
      document.removeEventListener('visibilitychange', onVisible);
      if (sentinel) void sentinel.release();
      sentinel = null;
    };
  }, [active]);
  return state;
}
