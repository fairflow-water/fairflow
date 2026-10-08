// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S3 — climate card and schematic basin (blueprint §5.2). Numbers come from the season.climate event; the river width
// is proportional to the inflow (a display scale, not a model value). Farms are filled by last season's adequacy band
// (outlines only in season 1), with the band word beside the name so the map never relies on colour alone.
import type { Band, Climate as ClimateEvent, PublicScenario } from '../room';

const PX_PER_MM3 = 3; // display scale for the river width
const fmt = (x: number): string => (Number.isInteger(x) ? String(x) : x.toFixed(1));
const cardWord: Record<string, string> = { wet: 'Wet', normal: 'Normal', dry: 'Dry' };

export function sentence(c: ClimateEvent): string {
  return `${cardWord[c.card] ?? c.card} year. ${fmt(c.inflow)} Mm³ arrived, ${fmt(c.reserve)} stay in the river, ${fmt(c.allocable)} to share.`;
}

function Shape({ shape, x, y, band }: { shape: string | undefined; x: number; y: number; band: Band | undefined }) {
  const size = 22;
  const className = band ? `scheme band-${band}` : 'scheme';
  if (shape === 'square') return <rect x={x - size / 2} y={y - size / 2} width={size} height={size} className={className} />;
  if (shape === 'triangle') {
    return <polygon points={`${x},${y - size / 2} ${x + size / 2},${y + size / 2} ${x - size / 2},${y + size / 2}`} className={className} />;
  }
  return <circle cx={x} cy={y} r={size / 2} className={className} />;
}

export function Climate({ climate, scenario, season, bands = null }: {
  climate: ClimateEvent; scenario: PublicScenario; season: number; bands?: Band[] | null;
}) {
  const width = climate.inflow * PX_PER_MM3;
  const schemes = [...scenario.schemes].sort((a, b) => a.seat - b.seat);
  return (
    <section aria-labelledby="climate-title" className="climate">
      <div className={`card card-${climate.card}`}>
        <p className="eyebrow">{climate.tutorial ? 'Practice round (not scored)' : `Season ${season}`}</p>
        <h2 id="climate-title">{sentence(climate)}</h2>
      </div>
      <svg viewBox="0 0 320 300" role="img" aria-label="Schematic basin: the river flows past the farms from upstream to the tail">
        <rect x={160 - width / 2} y={0} width={width} height={300} className="river" data-testid="river" />
        {schemes.map((s, i) => {
          const y = 60 + i * 90;
          const band = bands?.[scenario.schemes.indexOf(s)];
          return (
            <g key={s.id} data-testid={`farm-${s.id}`}>
              <Shape shape={s.shape} x={70} y={y} band={band} />
              <text x={100} y={y + 5} className="label">{s.name}{band ? ` · ${band}` : ''}</text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
