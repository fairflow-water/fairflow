// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S4 — lens vote (blueprint §5.2). Each row shows the engine's preview for this season: one bar per farm, filled to its
// share of need (acceptance: bar lengths equal the shares to 1 %). The academic name is a small subtitle (§5.1).
import { tally, type PublicScenario, type RoomView } from '../room';

const pct = (share: number): string => `${Math.round(share * 100)} %`;

export interface LensVoteProps {
  view: RoomView;
  scenario: PublicScenario;
  role: string; // 'authority', 'display' or a scheme id
  onIntent: (intent: Record<string, unknown>) => void;
}

export function LensVote({ view, scenario, role, onIntent }: LensVoteProps) {
  const climate = view.climate;
  if (!climate) return null;
  const counts = tally(view.votes);
  const isAuthority = role === 'authority';
  const isPlayer = scenario.schemes.some(s => s.id === role);
  const names = new Map(scenario.lenses.map(l => [l.id, l.plainName]));
  const schemes = [...scenario.schemes].sort((a, b) => a.seat - b.seat);
  return (
    <section aria-labelledby="vote-title" className="vote">
      <h2 id="vote-title">How do you share it?</h2>
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
              {isAuthority && view.phase === 'vote' && !proposed && (
                <button type="button" onClick={() => onIntent({ intent: 'propose', lens: p.lens })}>Propose</button>
              )}
              {isPlayer && view.phase === 'vote' && proposed && (
                <button type="button" aria-pressed={mine} onClick={() => onIntent({ intent: 'vote', lens: p.lens })}>
                  {mine ? 'Your vote' : 'Vote'}
                </button>
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
