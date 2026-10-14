// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// E7: the screen stays on during play, is taken again when the page comes back, and is let go at the end.
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useWakeLock } from './useWakeLock';

function fakeApi() {
  const sentinels: { release: ReturnType<typeof vi.fn>; fire: () => void }[] = [];
  const request = vi.fn(() => {
    let onRelease = () => undefined as void;
    const s = {
      release: vi.fn(() => Promise.resolve()),
      addEventListener: (_: 'release', fn: () => void) => { onRelease = fn; },
      fire: () => onRelease(),
    };
    sentinels.push(s);
    return Promise.resolve(s);
  });
  Object.defineProperty(navigator, 'wakeLock', { value: { request }, configurable: true });
  return { request, sentinels };
}

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { value: state, configurable: true });
  document.dispatchEvent(new Event('visibilitychange'));
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'wakeLock');
  Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
});

describe('Wake Lock during play (E7)', () => {
  it('holds the screen while active and lets it go when play ends', async () => {
    const { request, sentinels } = fakeApi();
    const { result, rerender } = renderHook(({ on }) => useWakeLock(on), { initialProps: { on: true } });
    await waitFor(() => expect(result.current).toBe('held'));
    expect(request).toHaveBeenCalledExactlyOnceWith('screen');
    rerender({ on: false });
    expect(sentinels[0]!.release).toHaveBeenCalledOnce();
    expect(result.current).toBe('off');
  });
  it('asks for nothing before play is active', () => {
    const { request } = fakeApi();
    const { result } = renderHook(() => useWakeLock(false));
    expect(request).not.toHaveBeenCalled();
    expect(result.current).toBe('off');
  });
  it('takes the lock again when the page comes back, after the browser let it go on hiding', async () => {
    const { request, sentinels } = fakeApi();
    const { result } = renderHook(() => useWakeLock(true));
    await waitFor(() => expect(result.current).toBe('held'));
    act(() => { setVisibility('hidden'); sentinels[0]!.fire(); }); // the browser releases a hidden page's lock
    expect(result.current).toBe('off');
    expect(request).toHaveBeenCalledOnce(); // not while hidden
    act(() => { setVisibility('visible'); });
    await waitFor(() => expect(result.current).toBe('held'));
    expect(request).toHaveBeenCalledTimes(2);
  });
  it('lets the lock go on unmount', async () => {
    const { sentinels } = fakeApi();
    const { result, unmount } = renderHook(() => useWakeLock(true));
    await waitFor(() => expect(result.current).toBe('held'));
    unmount();
    expect(sentinels[0]!.release).toHaveBeenCalledOnce();
  });
  it('says so where the API is missing or refuses, and never throws', async () => {
    const missing = renderHook(() => useWakeLock(true));
    expect(missing.result.current).toBe('unsupported');
    missing.unmount();
    Object.defineProperty(navigator, 'wakeLock', { value: { request: () => Promise.reject(new Error('NotAllowedError')) }, configurable: true });
    const refused = renderHook(() => useWakeLock(true));
    await waitFor(() => expect(refused.result.current).toBe('refused'));
  });
});
