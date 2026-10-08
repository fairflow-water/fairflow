// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// What a device shows for the table's current phase: climate and map (S3), the lens vote (S4) and floor vote, the
// private turn on a farm's own device (S6), the reveal (S7), the game end (S8), the debrief (S9) and the review (S10).
import { useState } from 'react';
import type { PublicScenario, RecordEvent, RoomView } from '../room';
import { Debrief } from './Debrief';
import { Climate } from './Climate';
import { FloorVote } from './FloorVote';
import { GameEnd } from './GameEnd';
import { LensVote } from './LensVote';
import { PrivateTurn } from './PrivateTurn';
import { Reveal } from './Reveal';
import { Review } from './Review';

export function Season({ view, scenario, role, onIntent, events = [], code = '' }: {
  view: RoomView; scenario: PublicScenario; role: string; onIntent: (intent: Record<string, unknown>) => void;
  events?: readonly RecordEvent[]; code?: string;
}) {
  const isPlayer = scenario.schemes.some(s => s.id === role);
  const [tab, setTab] = useState<'debrief' | 'review'>('debrief');
  if (view.phase === 'lobby') {
    return role === 'authority'
      ? (
        <>
          <button type="button" className="cta" onClick={() => onIntent({ intent: 'start_tutorial' })}>Start the practice round</button>
          <button type="button" onClick={() => onIntent({ intent: 'start_season' })}>Skip it and open season 1</button>
        </>
      )
      : <p className="waiting">Waiting for the facilitator to open season 1.</p>;
  }
  if (view.phase === 'ended' && view.debriefOpened) {
    return (
      <>
        {isPlayer && (
          <div role="tablist" aria-label="After the game" className="tabs">
            <button type="button" role="tab" aria-selected={tab === 'debrief'} onClick={() => setTab('debrief')}>Debrief</button>
            <button type="button" role="tab" aria-selected={tab === 'review'} onClick={() => setTab('review')}>Review form</button>
          </div>
        )}
        {isPlayer && tab === 'review'
          ? <Review storageKey={`fairflow.review.${code}.${role}`} saved={view.review} onIntent={onIntent} />
          : <Debrief view={view} scenario={scenario} events={events} />}
      </>
    );
  }
  if (view.phase === 'ended' && view.ended) {
    return <GameEnd end={view.ended} goal={view.myGoal} role={role} lenses={scenario.lenses}
      debriefOpened={view.debriefOpened} onIntent={onIntent} />;
  }
  if (!view.climate) return null;
  const last = view.tutorial ? view.tutorialResult : view.results[view.results.length - 1] ?? null;
  const banner = view.results[view.results.length - 1] ?? null; // S6 banner: last scored season
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
        ? <PrivateTurn key={view.season} turn={view.privateTurn} last={banner?.mine ?? null} demand={demand}
            decisionS={scenario.session?.decisionS ?? null}
            onCommit={(pumps, action) => onIntent({ intent: 'commit', pumps, action })} />
        : <p className="waiting">{!isPlayer ? 'Private turns: each farm decides on its own device.'
            : view.myCommit ? 'Committed. Waiting for the other farms.' : 'Opening your private turn…'}</p>)}
      {view.phase === 'reveal' && last && (
        <>
          <Reveal key={view.season} result={last.public} mine={last.mine} season={view.season} practice={view.tutorial} />
          {role === 'authority' && (
            <button type="button" className="cta" onClick={() => onIntent({ intent: 'start_season' })}>
              {view.tutorial ? 'Open season 1' : 'Open the next season'}
            </button>
          )}
        </>
      )}
    </>
  );
}
