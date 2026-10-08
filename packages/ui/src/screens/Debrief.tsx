// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S9 — the debrief replay (blueprint §5.2 S9, ADR 0003, ADR 0004). Season tabs; for the selected season the triangle,
// the two-needle gauge as used beside its as-allocated ghost, the two-line verdict, the equalisandum control (moves only
// the E_SE needle) and the F consumed/diverted toggle (moves only F); the welfare slider; per-farm pumping only if the
// table agreed (R19). With per-player results kept sealed, every value computed on actual use stays sealed too, since
// with the public allocation it would show who pumped (ADR 0004). Every number comes from the engine's events.
import { useState } from 'react';
import type { PublicScenario, RecordEvent, RoomView, SeasonResult } from '../room';
import { needleAngle } from './Reveal';

type Unit = 'claimant' | 'hectare' | 'person';
type Basis = 'consumed' | 'diverted';
const UNITS: { id: Unit; label: string }[] = [
  { id: 'claimant', label: 'per farm' }, { id: 'hectare', label: 'per hectare' }, { id: 'person', label: 'per person' },
];
const fmt = (x: number): string => (Number.isInteger(x) ? String(x) : x.toFixed(2));
const pct = (x: number): string => `${Math.round(x * 100)} %`;

function Needles({ pj, se, ghostPj, ghostSe }: { pj: number | null; se: number | null; ghostPj: number; ghostSe: number }) {
  const line = (value: number, cls: string, testid: string) => (
    <line x1={100} y1={100} x2={100} y2={20} className={cls} data-testid={testid} transform={`rotate(${needleAngle(value)} 100 100)`} />
  );
  return (
    <svg viewBox="0 0 200 110" role="img" aria-label="Fairness gauge: as used (solid) and as allocated (faint)">
      <path d="M 10 100 A 90 90 0 0 1 190 100" className="arc" />
      {line(ghostPj, 'needle pj ghost', 'ghost-pj')}
      {line(ghostSe, 'needle se ghost', 'ghost-se')}
      {pj !== null && line(pj, 'needle pj', 'used-pj')}
      {se !== null && line(se, 'needle se', 'used-se')}
      <text x={10} y={110} className="tick">−1</text>
      <text x={190} y={110} className="tick" textAnchor="end">1</text>
    </svg>
  );
}

/** The triangle stack (§2.5): equity, efficiency and sustainability ratios on three axes from the centre. */
function Triangle({ r1, r2, r3 }: { r1: number; r2: number; r3: number }) {
  const R = 80, cx = 100, cy = 95;
  const axis = (k: number, r: number) => {
    const a = -Math.PI / 2 + (k * 2 * Math.PI) / 3;
    return `${cx + r * R * Math.cos(a)},${cy + r * R * Math.sin(a)}`;
  };
  return (
    <svg viewBox="0 0 200 170" role="img" aria-label="Triangle: equity, efficiency and sustainability (outer edge = 1)">
      <polygon points={[0, 1, 2].map(k => axis(k, 1)).join(' ')} className="tri-frame" />
      <polygon points={[r1, r2, r3].map((r, k) => axis(k, Math.min(1, Math.max(0, r)))).join(' ')} className="tri" data-testid="triangle" />
      <text x={cx} y={8} className="tick" textAnchor="middle">equity</text>
      <text x={196} y={168} className="tick" textAnchor="end">efficiency</text>
      <text x={4} y={168} className="tick">sustainability</text>
    </svg>
  );
}

export function Debrief({ view, scenario, events }: { view: RoomView; scenario: PublicScenario; events: readonly RecordEvent[] }) {
  const results = view.results;
  const [k, setK] = useState(results.length - 1);
  const [unit, setUnit] = useState<Unit>('claimant');
  const [basis, setBasis] = useState<Basis>('consumed');
  const [g, setG] = useState(view.debriefWelfare?.start ?? 0);
  const r: SeasonResult | undefined = results[k];
  if (!r) return null;
  const lensName = (id: string) => scenario.lenses.find(l => l.id === id)?.plainName ?? id;
  const schemeName = (id: string) => scenario.schemes.find(s => s.id === id)?.name ?? id;
  const sealed = r.sealed;
  const alloc = r.public.asAllocated;
  const welfare = view.debriefWelfare?.seasons.find(w => w.season === r.season);
  const rows = welfare
    ? [...Object.entries(welfare.lenses).map(([lens, v]) => ({ key: lens, name: lensName(lens), value: v[g] ?? 0 })),
       ...(welfare.used ? [{ key: 'used', name: 'The table’s water as used', value: welfare.used[g] ?? 0 }] : [])]
        .sort((a, b) => b.value - a.value)
    : [];
  const steps = (view.debriefWelfare?.gammas.length ?? 1) - 1;

  function exportRecord() {
    const blob = new Blob([JSON.stringify({ exportedBy: 'fairflow', events }, null, 1)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'fairflow-season-record.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <section aria-labelledby="debrief-title" className="debrief-view">
      <h2 id="debrief-title">Debrief</h2>
      <div role="tablist" aria-label="Seasons" className="tabs">
        {results.map((x, i) => (
          <button key={x.season} type="button" role="tab" aria-selected={i === k} onClick={() => setK(i)}>Season {x.season}</button>
        ))}
      </div>

      {sealed ? (
        <>
          <Triangle r1={sealed.triangle.r1} r2={sealed.triangle.r2} r3={sealed.triangle.r3} />
          <p>Season score <strong data-testid="season-score">{fmt(sealed.triangle.score)}</strong></p>
          <Needles pj={sealed.ePJ} se={sealed.eSE[unit]} ghostPj={alloc.ePJ} ghostSe={alloc.eSE[unit]} />
          <p className="legend">
            <span className="key pj" /> fair shares of need {fmt(sealed.ePJ)} · <span className="key se" /> equal amounts {UNITS.find(u => u.id === unit)?.label} {fmt(sealed.eSE[unit])} · faint = as allocated
          </p>
          <div role="radiogroup" aria-label="Equal amounts of what?" className="segmented">
            {UNITS.map(u => (
              <button key={u.id} type="button" role="radio" aria-checked={unit === u.id} onClick={() => setUnit(u.id)}>{u.label}</button>
            ))}
          </div>
          <p data-testid="verdict">The table chose <strong>{lensName(sealed.verdict.voted)}</strong>.<br />
            The water as used came closest to <strong>{lensName(sealed.verdict.satisfied)}</strong> ({fmt(r.public.pumpsTotal)} Mm³ pumped).</p>
          <p data-testid="f-line">Water productivity as used: {fmt(sealed.F[basis])} of design, per m³ {basis}.
            <button type="button" aria-pressed={basis === 'diverted'} onClick={() => setBasis(b => (b === 'consumed' ? 'diverted' : 'consumed'))}>
              Per m³ {basis === 'consumed' ? 'diverted' : 'consumed'}
            </button>
          </p>
          <table className="sheet">
            <caption>Each farm this season</caption>
            <thead><tr><th scope="col">Farm</th><th scope="col">Pumped</th><th scope="col">Water used (allocated + pumped)</th><th scope="col">Harvest t</th><th scope="col">Points</th></tr></thead>
            <tbody>
              {sealed.roles.map((role, i) => (
                <tr key={role}>
                  <th scope="row">{schemeName(role)}</th>
                  <td>{fmt(sealed.pumpsBy[role] ?? 0)}</td><td>{fmt(sealed.W[i] ?? 0)}</td>
                  <td>{Math.round(sealed.Y[i] ?? 0)}</td><td>{fmt(sealed.points[i] ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <>
          <Needles pj={null} se={null} ghostPj={alloc.ePJ} ghostSe={alloc.eSE[unit]} />
          <p>As allocated: fair shares of need {fmt(alloc.ePJ)}, equal amounts per farm {fmt(alloc.eSE.claimant)}. The table pumped {fmt(r.public.pumpsTotal)} Mm³.</p>
          <p className="hint" data-testid="sealed-note">Each farm's pumping was kept private for this debrief. Values on the water as used stay sealed as well: together with the public allocation they would show who pumped.</p>
        </>
      )}

      {welfare && (
        <div className="welfare">
          <h3>How much more should water to the worst-off farm count?</h3>
          <input type="range" min={0} max={steps} step={1} value={g} onChange={e => setG(Number(e.target.value))}
            aria-label="Weight on the worst-off farm"
            aria-valuetext={g === 0 ? 'every share counts the same' : g === steps ? 'only the worst-off counts' : g === view.debriefWelfare?.start ? 'reference value' : 'in between'} />
          <div className="slider-ends"><span>every share counts the same</span><span>only the worst-off counts</span></div>
          <ol className="ranking" data-testid="ranking">
            {rows.map(row => (
              <li key={row.key} data-testid={`rank-${row.key}`}>
                <span>{row.name}</span>
                <span className="bar"><span className="fill" style={{ width: pct(row.value) }} /></span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <button type="button" onClick={exportRecord}>Export the record (roles, never names)</button>
    </section>
  );
}
