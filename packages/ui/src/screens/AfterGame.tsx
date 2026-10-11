// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0011, for a farm's own screen after the game: while research is enabled, what a player needs to withdraw (room
// code, farm, join date); and a way to leave, which clears this device's role token and review drafts for the room.
import { useState } from 'react';
import sheet from '../../../../content/information-sheet.json';
import { tokenStore } from '../api';

export function AfterGame({ code, role, farm, joinedOn, research }: {
  code: string; role: string; farm: string; joinedOn: string | undefined; research: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const [left, setLeft] = useState(false);
  if (left) return <p className="notice" role="status">You have left this game on this device. You can close this page.</p>;
  return (
    <aside className="after-game" aria-label="Leaving the game">
      {research && (
        <p data-testid="withdrawal">Room {code}, {farm}, joined {joinedOn ?? 'today'}. {sheet.withdrawal}</p>
      )}
      {confirming
        ? (
          <p>
            This device forgets your farm and your unsaved review drafts, and cannot return to this farm.{' '}
            <button type="button" onClick={() => { tokenStore.leave(code, role); setLeft(true); }}>Leave now</button>{' '}
            <button type="button" onClick={() => setConfirming(false)}>Stay</button>
          </p>
        )
        : <button type="button" onClick={() => setConfirming(true)}>Leave this game</button>}
    </aside>
  );
}
