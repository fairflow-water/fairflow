// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// E7 (maintainer's decision, 2026-10-15): the screen stays on for the session and is let go once the game has ended
// and either the review form is sent or the device has been idle for the registry's session.wakeLockIdleReleaseMin.
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import form from '../../../content/review-form.json';
import registry from '../../scenarios/parameters.json';
import { IDLE_RELEASE_MS, formSent, screenStaysOn, useIdle } from './wakePolicy';

const items = form.parts.flatMap(p => p.items.map(i => i.id));
const all = Object.fromEntries(items.map(id => [id, 'an answer'])); // test input: every item saved
const minutes = Number(registry.parameters.find(p => p.key === 'session.wakeLockIdleReleaseMin')!.default);
const MIN_MS = 60_000; // milliseconds per minute

afterEach(() => { vi.useRealTimers(); });

describe('when the screen is let go (E7)', () => {
  it('reads the idle length from the registry', () => {
    expect(IDLE_RELEASE_MS).toBe(minutes * MIN_MS);
  });
  it('a review form counts as sent once every item is saved', () => {
    expect(formSent({})).toBe(false);
    expect(formSent(Object.fromEntries(items.slice(1).map(id => [id, 'x'])))).toBe(false);
    expect(formSent(all)).toBe(true);
  });
  it('stays on during play whatever happens, and goes off when the room is gone', () => {
    expect(screenStaysOn({ link: 'open', phase: 'private', review: all, idle: true })).toBe(true);
    expect(screenStaysOn({ link: 'gone', phase: 'vote', review: {}, idle: false })).toBe(false);
  });
  it('after the game: on until the form is sent or the device is idle, whichever comes first', () => {
    expect(screenStaysOn({ link: 'open', phase: 'ended', review: {}, idle: false })).toBe(true);
    expect(screenStaysOn({ link: 'open', phase: 'ended', review: all, idle: false })).toBe(false);
    expect(screenStaysOn({ link: 'open', phase: 'ended', review: {}, idle: true })).toBe(false);
  });
  it('counts idle time only while active, and any input starts it again', () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ on }) => useIdle(on, IDLE_RELEASE_MS), { initialProps: { on: false } });
    act(() => { vi.advanceTimersByTime(IDLE_RELEASE_MS); });
    expect(result.current).toBe(false); // not counting during play
    rerender({ on: true });
    act(() => { vi.advanceTimersByTime(IDLE_RELEASE_MS - 1); });
    act(() => { document.dispatchEvent(new Event('pointerdown')); }); // a tap just before the end
    act(() => { vi.advanceTimersByTime(IDLE_RELEASE_MS - 1); });
    expect(result.current).toBe(false);
    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current).toBe(true);
    act(() => { document.dispatchEvent(new Event('keydown')); }); // back at the device: the screen is wanted again
    expect(result.current).toBe(false);
  });
  it('stops listening when play resumes or the page closes', () => {
    vi.useFakeTimers();
    const add = vi.spyOn(document, 'addEventListener');
    const remove = vi.spyOn(document, 'removeEventListener');
    try {
      const { rerender, unmount } = renderHook(({ on }) => useIdle(on, IDLE_RELEASE_MS), { initialProps: { on: true } });
      const added = add.mock.calls.length;
      rerender({ on: false });
      expect(remove.mock.calls.length).toBe(added);
      rerender({ on: true });
      unmount();
      expect(remove.mock.calls.length).toBe(2 * added);
    } finally { // a failed assertion must not leave the spies on document for later tests
      add.mockRestore();
      remove.mockRestore();
    }
  });
  it('input after play resumes no longer starts an idle count: the capture listeners are really removed', () => {
    vi.useFakeTimers();
    try {
      const { result, rerender } = renderHook(({ on }) => useIdle(on, IDLE_RELEASE_MS), { initialProps: { on: true } });
      rerender({ on: false }); // test input: play resumes, so idle time stops counting
      act(() => { document.dispatchEvent(new Event('pointerdown')); }); // test input: a tap during play
      act(() => { vi.advanceTimersByTime(IDLE_RELEASE_MS); });
      expect(result.current).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});
