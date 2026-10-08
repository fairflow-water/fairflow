// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S8 — game end (blueprint §5.2): the revealed length (and a time-box badge), the collective score with the crop-failure
// flag, goals met or missed (each farm sees only its own), and for the facilitator the engine's three-line brief and
// the way into the debrief: the safety norm first, then "reveal who pumped?" (R19, §5.3).
import type { GameEnd as End, GoalResult, PublicLens } from '../room';

const pct = (x: number): string => `${Math.round(x * 100)} %`;
const SAFETY_NORM = 'The rules made pumping rational; we debrief the rules, not the person.'; // §5.3
const GOAL_TEXT: Record<string, (t: number) => string> = {
  livelihood_share: t => `keep your livelihood points at least ${pct(t)} of what full water would have given`,
  adequacy_floor: t => `never fall below ${pct(t)} of your need`,
  adequacy_in_half_seasons: t => `reach ${pct(t)} of your need in at least half the seasons`,
};

/** "Same share of need (seasons 1–6) → …": the lens chosen in each season, consecutive repeats grouped. */
export function lensRuns(bySeason: readonly string[], name: (id: string) => string): string {
  const runs: { lens: string; from: number; to: number }[] = [];
  bySeason.forEach((lens, i) => {
    const last = runs[runs.length - 1];
    if (last && last.lens === lens) last.to = i + 1;
    else runs.push({ lens, from: i + 1, to: i + 1 });
  });
  return runs.map(r => `${name(r.lens)} (${r.from === r.to ? `season ${r.from}` : `seasons ${r.from}–${r.to}`})`).join(' → ');
}

export function GameEnd({ end, goal, role, lenses, debriefOpened, onIntent }: {
  end: End; goal: GoalResult | null; role: string; lenses: PublicLens[]; debriefOpened: boolean;
  onIntent: (intent: Record<string, unknown>) => void;
}) {
  const name = (id: string) => lenses.find(l => l.id === id)?.plainName ?? id;
  return (
    <section aria-labelledby="end-title" className="end">
      <h2 id="end-title">The game lasted {end.seasonsPlayed} seasons{end.truncated ? ' (time-boxed)' : ''}.</h2>
      <p>Collective score: <strong data-testid="score">{pct(end.collectiveScore)}</strong>{end.cropFailureFlag ? ' · a crop failed' : ''}</p>
      {end.authorityGoal && (
        <p>Authority's goal (the table's total pumping, averaged over seasons, at most {end.authorityGoal.maxMeanPumping} Mm³ a season): {end.authorityGoal.met ? 'met' : 'missed'}.</p>
      )}
      {goal && (
        <p className="mine">Your goal, to {GOAL_TEXT[goal.kind]?.(goal.threshold) ?? goal.kind}: <strong>{goal.met ? 'met' : 'missed'}</strong>.</p>
      )}
      {role === 'authority' && end.brief && (
        <aside aria-label="Debrief brief (facilitator)">
          <h3>Debrief brief</h3>
          <ul>
            <li>Heaviest pumping: {end.brief.heaviestPumping ? `season ${end.brief.heaviestPumping.season}, ${end.brief.heaviestPumping.pumpsTotal} Mm³` : 'none'}.</li>
            <li>Lens by season: {lensRuns(end.brief.lensBySeason, name)} ({end.brief.lensChanges} changes).</li>
            <li>Floor votes held: {end.brief.floorVotes}.</li>
          </ul>
          {!debriefOpened && (
            <div className="debrief">
              <p><strong>Say first:</strong> {SAFETY_NORM}</p>
              <button type="button" onClick={() => onIntent({ intent: 'open_debrief', perPlayer: true })}>Open the debrief: reveal who pumped</button>
              <button type="button" onClick={() => onIntent({ intent: 'open_debrief', perPlayer: false })}>Open the debrief: totals only</button>
            </div>
          )}
        </aside>
      )}
    </section>
  );
}
