// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S4 — lens vote (blueprint §5.2). Each row shows the engine's preview for this season: one bar per scheme, filled to its
// share of need (acceptance: bar lengths equal the shares to 1 %). The academic name is a small subtitle (§5.1).
import { useState } from 'react';
import { tally, type PublicScenario, type RoomView } from '../room';

const pct = (share: number): string => `${Math.round(share * 100)} %`;

export interface LensVoteProps {
  view: RoomView;
  scenario: PublicScenario;
  role: string; // 'authority', 'display' or a scheme id
  onIntent: (intent: Record<string, unknown>) => void;
}

export function LensVote({ view, scenario, role, onIntent }: LensVoteProps) {
  const [confirming, setConfirming] = useState<string | null>(null); // the lens the Authority is about to veto
  const climate = view.climate;
  if (!climate) return null;
  const counts = tally(view.votes);
  const isAuthority = role === 'authority';
  const isPlayer = scenario.schemes.some(s => s.id === role);
  const names = new Map(scenario.lenses.map(l => [l.id, l.plainName]));
  const schemes = [...scenario.schemes].sort((a, b) => a.seat - b.seat);
  // R8: one veto per game, not in the practice round, and only while another proposal would remain to re-vote on
  const canVeto = isAuthority && view.phase === 'vote' && !view.tutorial && !view.vetoUsed && view.proposals.length > 1;
  return (
    <section aria-labelledby="vote-title" className="vote">
      <h2 id="vote-title">How do you share it?</h2>
      {view.vetoed && (
        <p className="banner" role="status">
          The Authority vetoed {names.get(view.vetoed) ?? view.vetoed}. Vote again on the remaining lenses.
        </p>
      )}
      <ul className="lenses">
        {climate.previews.map(p => {
          const proposed = view.proposals.includes(p.lens);
          const mine = view.votes[role] === p.lens;
          return (
            <li key={p.lens} className={proposed ? 'lens proposed' : 'lens'} data-testid={`lens-${p.lens}`}>
              <div className="lens-head">
                <strong>{names.get(p.lens) ?? p.lens}</strong>
                <small className="academic">{p.lens.replace('_', ' ')}</small>
                {proposed && <span className="tally" aria-label={`${counts[p.lens] ?? 0} votes`}>{counts[p.lens] ?? 0}</span>}
              </div>
              <div className="bars">
                {schemes.map((s, i) => {
                  const share = p.shareOfNeed[i] ?? 0;
                  return (
                    <div className="bar-row" key={s.id}>
                      <span className="bar-name">{s.name}</span>
                      <span className="bar" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(share * 100)}
                        aria-label={`${s.name}: ${pct(share)} of need`}>
                        <span className="fill" style={{ width: `${Math.min(share, 1) * 100}%` }} data-testid={`fill-${p.lens}-${s.id}`} />
                      </span>
                      <span className="bar-pct">{pct(share)}</span>
                    </div>
                  );
                })}
              </div>
              {p.floorVoteNeeded && <p className="hint">Not enough for every minimum: the table would choose how to cut.</p>}
              {view.vetoed === p.lens && <p className="hint">Vetoed this season.</p>}
              {isAuthority && view.phase === 'vote' && !proposed && view.vetoed !== p.lens && (
                <button type="button" onClick={() => onIntent({ intent: 'propose', lens: p.lens })}>Propose</button>
              )}
              {isPlayer && view.phase === 'vote' && proposed && (
                <button type="button" aria-pressed={mine} onClick={() => onIntent({ intent: 'vote', lens: p.lens })}>
                  {mine ? 'Your vote' : 'Vote'}
                </button>
              )}
              {canVeto && proposed && confirming !== p.lens && (
                <button type="button" onClick={() => setConfirming(p.lens)}>Veto</button>
              )}
              {canVeto && proposed && confirming === p.lens && (
                <span role="group" aria-label="Confirm the veto">
                  <span>Use the one veto of the game on this lens? Every vote so far is cleared.</span>
                  <button type="button" onClick={() => { setConfirming(null); onIntent({ intent: 'veto', lens: p.lens }); }}>
                    Confirm veto
                  </button>
                  <button type="button" onClick={() => setConfirming(null)}>Cancel</button>
                </span>
              )}
              {isAuthority && view.phase === 'tiebreak' && view.leaders.includes(p.lens) && (
                <button type="button" onClick={() => onIntent({ intent: 'break_tie', lens: p.lens })}>Break the tie</button>
              )}
            </li>
          );
        })}
      </ul>
      {isAuthority && view.phase === 'vote' && (
        <button type="button" className="cta" onClick={() => onIntent({ intent: 'close_vote' })}>Close the vote</button>
      )}
    </section>
  );
}
