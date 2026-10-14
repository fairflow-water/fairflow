// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// What a device shows for the table's current phase: climate and map (S3), the lens vote (S4) and floor vote, the
// private turn on a scheme's own device (S6), the reveal (S7), the game end (S8), the debrief (S9) and the review (S10).
import { useState } from 'react';
import type { PublicScenario, RecordEvent, RoomView } from '../room';
import { Debrief } from './Debrief';
import { Climate } from './Climate';
import { FloorVote } from './FloorVote';
import { AfterGame } from './AfterGame';
import { GameEnd } from './GameEnd';
import { LensVote } from './LensVote';
import { PrivateTurn } from './PrivateTurn';
import { Reveal } from './Reveal';
import { Review } from './Review';

export function Season({ view, scenario, role, onIntent, trySend, resync, clockOffsetMs = 0, events = [], code = '' }: {
  view: RoomView; scenario: PublicScenario; role: string; onIntent: (intent: Record<string, unknown>) => void;
  /** Sends silently and says whether it went out (the private turn retries a commit that did not). */
  trySend?: (intent: Record<string, unknown>) => boolean;
  resync?: number; clockOffsetMs?: number; events?: readonly RecordEvent[]; code?: string;
}) {
  const commitIntent = trySend ?? ((intent: Record<string, unknown>) => { onIntent(intent); return true; });
  const isPlayer = scenario.schemes.some(s => s.id === role);
  const [tab, setTab] = useState<'debrief' | 'review'>('debrief');
  const leaving = isPlayer && (
    <AfterGame code={code} role={role} scheme={scenario.schemes.find(s => s.id === role)?.name ?? role}
      joinedOn={view.joinedOn[role]} research={view.researchEnabled} />
  );
  if (view.phase === 'lobby') {
    const missing = scenario.schemes.filter(x => !view.seated.includes(x.id));
    return role === 'authority'
      ? (
        <>
          <h2>Irrigation schemes at the table</h2>
          <ul className="seats" aria-label="Irrigation schemes at the table">
            {scenario.schemes.map(x => (
              <li key={x.id}>{x.name}: {view.seated.includes(x.id) ? 'joined' : 'waiting to join'}</li>
            ))}
          </ul>
          {missing.length > 0 && (
            <p className="waiting">Every irrigation scheme needs a player before the game starts ({missing.length} still to join). Each player joins on their own phone or browser.</p>
          )}
          <button type="button" className="cta" disabled={missing.length > 0} onClick={() => onIntent({ intent: 'start_tutorial' })}>Start the practice round</button>
          <button type="button" disabled={missing.length > 0} onClick={() => onIntent({ intent: 'start_season' })}>Skip it and open season 1</button>
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
        {leaving}
      </>
    );
  }
  if (view.phase === 'ended' && view.ended) {
    return (
      <>
        <GameEnd end={view.ended} goal={view.myGoal} role={role} lenses={scenario.lenses}
          debriefOpened={view.debriefOpened} onIntent={onIntent} />
        {leaving}
      </>
    );
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
      {(view.phase === 'vote' || view.phase === 'tiebreak') && <LensVote view={view} scenario={scenario} role={role} onIntent={onIntent} clockOffsetMs={clockOffsetMs} />}
      {view.phase === 'floor_vote' && <FloorVote view={view} role={role} isPlayer={isPlayer} onIntent={onIntent} />}
      {view.phase === 'private' && (isPlayer && view.privateTurn && !view.myCommit
        ? <PrivateTurn key={view.season} turn={view.privateTurn} last={banner?.mine ?? null} demand={demand}
            decisionS={scenario.session?.decisionS ?? null} clockOffsetMs={clockOffsetMs} resync={resync}
            onCommit={(pumps, action, autoCommitted) => commitIntent({ intent: 'commit', pumps, action, ...(autoCommitted ? { autoCommitted } : {}) })} />
        : <p className="waiting">{!isPlayer ? 'Private turns: the player for each scheme decides on their own device.'
            : view.myCommit ? 'Committed. Waiting for the other schemes.' : 'Opening your private turn…'}</p>)}
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
