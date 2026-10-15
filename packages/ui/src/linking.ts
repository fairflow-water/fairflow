// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// R3, §6.2 `linking.code` (ADR 0016, proposed): the personal linking code is made before the session on the player's
// own phone and kept there, so the join on the day can send it without anyone typing at the table. Storage failures
// (private windows, blocked storage) are tolerated: the player then joins without a code.
import recipe from '../../../content/linking-code.json';

const KEY = 'fairflow.linkingCode';

/** Capitals and digits only, within the bound the engine shares (content/linking-code.json maxLength). */
export function normaliseCode(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, recipe.maxLength);
}

export const linkingStore = {
  get(): string | null {
    try { return localStorage.getItem(KEY); } catch { return null; }
  },
  set(code: string): void {
    try { localStorage.setItem(KEY, code); } catch { /* storage unavailable: join without a code */ }
  },
  clear(): void {
    try { localStorage.removeItem(KEY); } catch { /* storage unavailable: nothing was kept */ }
  },
};
