// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// When the screen may lock (E7, blueprint §5.4 "a Wake Lock for the session"). The maintainer's convention
// (2026-10-15, registry session.wakeLockIdleReleaseMin): it stays on through play, and once the game has ended it is
// let go when the review form is sent or the device has been idle that long, whichever comes first. During play a
// projector or a waiting phone has no input for long stretches, so idle time counts only after the game.
import { useEffect, useState } from 'react';
import form from '../../../content/review-form.json';
import registry from '../../scenarios/parameters.json';
import type { LinkStatus } from './api';

const MIN_MS = 60_000; // milliseconds per minute
const idleMin = registry.parameters.find(p => p.key === 'session.wakeLockIdleReleaseMin')?.default;
if (typeof idleMin !== 'number') throw new Error('registry: session.wakeLockIdleReleaseMin is missing'); // never NaN
export const IDLE_RELEASE_MS = idleMin * MIN_MS;
const INPUT = ['pointerdown', 'keydown', 'touchstart', 'wheel', 'input'] as const; // someone is at the device

const ITEMS = form.parts.flatMap(p => p.items.map(i => i.id));

/** The review form is sent once every item has a saved answer (S10 saves item by item). */
export function formSent(review: Record<string, string>): boolean {
  return ITEMS.every(id => (review[id] ?? '') !== '');
}

export function screenStaysOn(s: { link: LinkStatus | null; phase: string; review: Record<string, string>; idle: boolean }): boolean {
  if (s.link === 'gone') return false;
  if (s.phase !== 'ended') return true;
  return !formSent(s.review) && !s.idle;
}

/** True once `active` has held for `ms` with no input; any input makes it false and starts the count again. */
export function useIdle(active: boolean, ms: number): boolean {
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    if (!active) { setIdle(false); return undefined; }
    let timer = setTimeout(() => setIdle(true), ms);
    const onInput = () => { clearTimeout(timer); setIdle(false); timer = setTimeout(() => setIdle(true), ms); };
    for (const type of INPUT) document.addEventListener(type, onInput, { capture: true, passive: true });
    return () => {
      clearTimeout(timer);
      for (const type of INPUT) document.removeEventListener(type, onInput, { capture: true });
    };
  }, [active, ms]);
  return idle;
}
