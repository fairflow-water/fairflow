// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0003 — when "Enough first" wins but the water cannot cover every minimum, the table chooses how to cut.
// Labels are the working labels in content/floor-rules.json.
import floorRules from '../../../../content/floor-rules.json';
import { tally, type RoomView } from '../room';

export function FloorVote({ view, role, isPlayer, onIntent }: {
  view: RoomView; role: string; isPlayer: boolean; onIntent: (intent: Record<string, unknown>) => void;
}) {
  const counts = tally(view.floorVotes);
  return (
    <section aria-labelledby="floor-title" className="floor">
      <h2 id="floor-title">Not enough for everyone's minimum. How do you cut?</h2>
      <ul className="options">
        {floorRules.options.map(o => (
          <li key={o.rule}>
            <strong>{o.label}</strong>
            <p>{o.explain}</p>
            <span className="tally">{counts[o.rule] ?? 0}</span>
            {isPlayer && (
              <button type="button" aria-pressed={view.floorVotes[role] === o.rule} onClick={() => onIntent({ intent: 'floor_vote', rule: o.rule })}>
                Choose
              </button>
            )}
          </li>
        ))}
      </ul>
      {role === 'authority' && (
        <button type="button" className="cta" onClick={() => onIntent({ intent: 'close_floor_vote' })}>Close the vote</button>
      )}
    </section>
  );
}
