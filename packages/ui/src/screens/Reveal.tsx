// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S7 — the three-beat reveal (blueprint §5.2) in the form ADR 0004 decided: during play the table sees total pumping,
// the coarse tank and the sustainability band word, and the equity and efficiency dials as allocated; actual-use values
// wait for the debrief. A farm also sees its own results, privately. Band words make every dial readable without colour.
import { useState } from 'react';
import type { MyResult, PublicResult } from '../room';

const fmt = (x: number): string => (Number.isInteger(x) ? String(x) : x.toFixed(1));
const signed = (x: number): string => `${x >= 0 ? '+' : '−'}${fmt(Math.abs(x))}`;
const SUSTAIN: Record<string, string> = { good: 'within renewable supply', warning: 'above renewable supply', unsustainable: 'far above renewable supply' };

/** Needle angle for an equity value: the dial shows 1 − CV clipped to [−1, 1] (§2.5), from left (−1) to right (1). */
export const needleAngle = (value: number): number => ((Math.min(1, Math.max(-1, value)) + 1) / 2) * 180 - 90;

function Gauge({ pj, se }: { pj: number; se: number }) {
  const needle = (value: number, cls: string, testid: string) => (
    <line x1={100} y1={100} x2={100} y2={20} className={cls} data-testid={testid}
      transform={`rotate(${needleAngle(value)} 100 100)`} />
  );
  return (
    <svg viewBox="0 0 200 110" role="img" aria-label={`Fair shares of need ${fmt(pj)}, equal amounts ${fmt(se)} (as allocated)`}>
      <path d="M 10 100 A 90 90 0 0 1 190 100" className="arc" />
      {needle(pj, 'needle pj', 'needle-pj')}
      {needle(se, 'needle se', 'needle-se')}
      <text x={10} y={110} className="tick">−1</text>
      <text x={190} y={110} className="tick" textAnchor="end">1</text>
    </svg>
  );
}

export function Reveal({ result, mine, season, practice = false }: {
  result: PublicResult; mine: MyResult | null; season: number; practice?: boolean;
}) {
  const [beat, setBeat] = useState(0);
  const bands = result.bands;
  const beats = [
    <div key="water">
      <h3>The table pumped {fmt(result.pumpsTotal)} Mm³.</h3>
      <p>The aquifer is at about {fmt(result.observedStockNext)} Mm³. Water use is {SUSTAIN[result.sustainabilityBand] ?? result.sustainabilityBand} ({result.sustainabilityBand}).</p>
      {result.aquiferFull && <p data-testid="full">The aquifer is full: any more recharge flows on out of the basin.</p>}
    </div>,
    <div key="equity">
      <h3>How fair was the sharing?</h3>
      <Gauge pj={result.asAllocated.ePJ} se={result.asAllocated.eSE.claimant} />
      <p className="legend"><span className="key pj" /> fair shares of need · <span className="key se" /> equal amounts</p>
      <p>As allocated, fair shares of need are {bands?.ePJ ?? '—'}; equal amounts are {bands?.eSE ?? '—'}.</p>
    </div>,
    <div key="productive">
      <h3>How productive was the water?</h3>
      <p>As allocated, the water's use is {bands?.F ?? '—'} ({fmt(result.asAllocated.F.consumed)} of design productivity).</p>
    </div>,
  ];
  return (
    <section aria-labelledby="reveal-title" className="reveal">
      <h2 id="reveal-title">{practice ? 'Practice round: what happened (not scored)' : `Season ${season}: what happened`}</h2>
      {beats[beat]}
      {beat < beats.length - 1
        ? <button type="button" onClick={() => setBeat(b => b + 1)}>Next</button>
        : null}
      {mine && (
        <aside className="mine" aria-label="Your farm (only you see this)">
          <h3>Your farm</h3>
          <p>Harvest {fmt(mine.Y)} t, {signed(mine.points)} points this season; {fmt(mine.L)} points in total.</p>
        </aside>
      )}
    </section>
  );
}
