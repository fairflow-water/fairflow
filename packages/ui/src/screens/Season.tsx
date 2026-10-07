// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// What a device shows for the table's current phase: climate and map (S3), the lens vote (S4) and floor vote, the
// private turn on a farm's own device (S6), the reveal (S7) and the game end (S8).
import type { PublicScenario, RoomView } from '../room';
import { Climate } from './Climate';
import { FloorVote } from './FloorVote';
import { GameEnd } from './GameEnd';
import { LensVote } from './LensVote';
import { PrivateTurn } from './PrivateTurn';
import { Reveal } from './Reveal';

export function Season({ view, scenario, role, onIntent }: {
  view: RoomView; scenario: PublicScenario; role: string; onIntent: (intent: Record<string, unknown>) => void;
}) {
  const isPlayer = scenario.schemes.some(s => s.id === role);
  if (view.phase === 'lobby') {
    return role === 'authority'
      ? <button type="button" className="cta" onClick={() => onIntent({ intent: 'start_season' })}>Open season 1</button>
      : <p className="waiting">Waiting for the facilitator to open season 1.</p>;
  }
  if (view.phase === 'ended' && view.ended) {
    return <GameEnd end={view.ended} goal={view.myGoal} role={role} lenses={scenario.lenses}
      debriefOpened={view.debriefOpened} onIntent={onIntent} />;
  }
  if (!view.climate) return null;
  const last = view.results[view.results.length - 1] ?? null;
  const demand = view.climate.schemes?.find(s => s.id === role)?.demandMm3 ?? null;
  return (
    <>
      {view.aquifer !== null && <p className="aquifer" data-testid="aquifer">Aquifer: about {view.aquifer} Mm³</p>}
      {view.phase !== 'reveal' && (
        <Climate climate={view.climate} scenario={scenario} season={view.season} bands={view.mapBands} />
      )}
      {(view.phase === 'vote' || view.phase === 'tiebreak') && <LensVote view={view} scenario={scenario} role={role} onIntent={onIntent} />}
      {view.phase === 'floor_vote' && <FloorVote view={view} role={role} isPlayer={isPlayer} onIntent={onIntent} />}
      {view.phase === 'private' && (isPlayer && view.privateTurn && !view.myCommit
        ? <PrivateTurn key={view.season} turn={view.privateTurn} last={last?.mine ?? null} demand={demand}
            decisionS={scenario.session?.decisionS ?? null}
            onCommit={(pumps, action) => onIntent({ intent: 'commit', pumps, action })} />
        : <p className="waiting">{!isPlayer ? 'Private turns: each farm decides on its own device.'
            : view.myCommit ? 'Committed. Waiting for the other farms.' : 'Opening your private turn…'}</p>)}
      {view.phase === 'reveal' && last && (
        <>
          <Reveal key={view.season} result={last.public} mine={last.mine} season={view.season} />
          {role === 'authority' && (
            <button type="button" className="cta" onClick={() => onIntent({ intent: 'start_season' })}>Open the next season</button>
          )}
        </>
      )}
    </>
  );
}
