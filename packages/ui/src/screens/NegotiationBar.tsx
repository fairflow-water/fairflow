// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S4's shrinking negotiation bar (blueprint §5.2: "seconds only in the last 30"). It runs to the server's deadline
// (ADR 0014): the record time of season.climate plus the scenario's negotiationS for the season (R20: 3:00 in seasons
// 0–2, 4:00 from season 3), on the server's clock, so a reload continues it. At zero the server closes the vote.
import { useEffect, useState } from 'react';

const MS = 1000; // layout: milliseconds per second
const TICK_MS = 250; // layout: how often the bar is redrawn
const SECONDS_SHOWN_FROM_S = 30; // §5.2 S4: "seconds only in the last 30"
const LAST_SHORT_SEASON = 2; // R20 and session.negotiationS.seasons0to2: the short negotiation runs in seasons 0–2

export interface NegotiationBarProps {
  openedAt: string;
  season: number;
  negotiationS: { seasons0to2: number; from3: number };
  clockOffsetMs?: number; // the server's clock minus this device's (ADR 0013)
}

export function NegotiationBar({ openedAt, season, negotiationS, clockOffsetMs = 0 }: NegotiationBarProps) {
  const lengthS = season <= LAST_SHORT_SEASON ? negotiationS.seasons0to2 : negotiationS.from3;
  const deadline = Date.parse(openedAt) + lengthS * MS; // NaN for an unreadable time: then no bar is drawn
  const left = () => Math.max(0, Math.ceil((deadline - (Date.now() + clockOffsetMs)) / MS));
  const [leftS, setLeftS] = useState(left);
  useEffect(() => {
    setLeftS(left());
    const tick = setInterval(() => setLeftS(left()), TICK_MS);
    return () => clearInterval(tick);
  }, [deadline, clockOffsetMs]);
  if (!Number.isFinite(deadline) || !(lengthS > 0)) return null; // the engine refuses such a scenario; never draw NaN
  return (
    <div className="negotiation" role="timer" aria-label="Time left to negotiate">
      <span className="bar" role="meter" aria-label="Negotiation time left" aria-valuemin={0} aria-valuemax={lengthS}
        aria-valuenow={leftS}>
        <span className="fill" data-testid="negotiation-fill" style={{ width: `${(leftS / lengthS) * 100}%` }} />
      </span>
      {leftS <= SECONDS_SHOWN_FROM_S && <span data-testid="negotiation-seconds">{leftS} s</span>}
    </div>
  );
}
