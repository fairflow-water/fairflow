// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// What a device shows for the table's current phase. Screens after the vote (S6 private turn, S7 reveal, S8 game end)
// are the next build step (ADR 0005, week 2); until then this says what the table is waiting for.
import type { PublicScenario, RoomView } from '../room';
import { Climate } from './Climate';
import { FloorVote } from './FloorVote';
import { LensVote } from './LensVote';

export function Season({ view, scenario, role, onIntent }: {
  view: RoomView; scenario: PublicScenario; role: string; onIntent: (intent: Record<string, unknown>) => void;
}) {
  const isPlayer = scenario.schemes.some(s => s.id === role);
  if (view.phase === 'lobby') {
    return role === 'authority'
      ? <button type="button" className="cta" onClick={() => onIntent({ intent: 'start_season' })}>Open season 1</button>
      : <p className="waiting">Waiting for the facilitator to open season 1.</p>;
  }
  if (!view.climate) return null;
  return (
    <>
      <Climate climate={view.climate} scenario={scenario} season={view.season} />
      {(view.phase === 'vote' || view.phase === 'tiebreak') && <LensVote view={view} scenario={scenario} role={role} onIntent={onIntent} />}
      {view.phase === 'floor_vote' && <FloorVote view={view} role={role} isPlayer={isPlayer} onIntent={onIntent} />}
      {view.phase === 'private' && <p className="waiting">Private turns: each farm decides on its own phone (next screen to build).</p>}
      {view.phase === 'reveal' && role === 'authority' && (
        <button type="button" className="cta" onClick={() => onIntent({ intent: 'start_season' })}>Open the next season</button>
      )}
      {view.phase === 'ended' && <p className="waiting">The game has ended.</p>}
    </>
  );
}
