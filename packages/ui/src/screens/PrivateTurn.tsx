// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S6 — the private turn (blueprint §5.2, R10, R20). This farm's last results, a 0–cap pump stepper framed as borrowing,
// the action tokens collapsed to one line, and the engine's preview of harvest and points for the current choice.
// The countdown runs from the scenario's decision time and commits the current choice when it ends; a commit can be
// undone for 3 s. Every number comes from the engine's private.opened and season.resolved events.
import { useEffect, useRef, useState } from 'react';
import type { MyResult, PrivateTurn as Turn } from '../room';

const UNDO_MS = 3000; // §5.2 S6 "hold-to-commit with 3 s undo"
const fmt = (x: number, digits = 1): string => (Number.isInteger(x) ? String(x) : x.toFixed(digits));
const signed = (x: number): string => `${x >= 0 ? '+' : '−'}${fmt(Math.abs(x))}`;
const ACTION_TEXT: Record<string, { name: string; effect: string }> = {
  orchard: { name: 'Orchard', effect: 'From next season: a more valuable crop that needs more water.' },
  drip: { name: 'Drip', effect: 'From next season: less water diverted for the same harvest.' },
  expand: { name: 'Expand', effect: 'From next season: more land, more water needed, more harvest.' },
};

export interface PrivateTurnProps {
  turn: Turn;
  last: MyResult | null;
  demand: number | null;
  decisionS: number | null;
  onCommit: (pumps: number, action: string | null) => void;
}

export function PrivateTurn({ turn, last, demand, decisionS, onCommit }: PrivateTurnProps) {
  const [pumps, setPumps] = useState(0);
  const [action, setAction] = useState<string | null>(null);
  const [openActions, setOpenActions] = useState(false);
  const [pending, setPending] = useState(false);
  const [left, setLeft] = useState<number | null>(decisionS);
  const choice = useRef({ pumps, action });
  choice.current = { pumps, action };
  const undo = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sent = useRef(false);

  const send = (p: number, a: string | null) => {
    if (sent.current) return;
    sent.current = true;
    onCommit(p, a);
  };

  useEffect(() => {
    if (decisionS === null) return undefined;
    const started = Date.now();
    const tick = setInterval(() => {
      const remaining = Math.max(0, decisionS - Math.floor((Date.now() - started) / 1000));
      setLeft(remaining);
      if (remaining === 0) {
        clearInterval(tick);
        send(choice.current.pumps, choice.current.action); // R20: auto-commit the current choice
      }
    }, 250);
    return () => clearInterval(tick);
  }, [decisionS]);

  useEffect(() => () => { if (undo.current) clearTimeout(undo.current); }, []);

  const option = turn.options.find(o => o.pumps === pumps) ?? turn.options[0];
  const points = option ? option.points[action ?? 'none'] ?? option.points['none'] ?? 0 : 0;

  function commit() {
    setPending(true);
    undo.current = setTimeout(() => send(pumps, action), UNDO_MS);
  }
  function cancel() {
    if (undo.current) clearTimeout(undo.current);
    setPending(false);
  }

  return (
    <section aria-labelledby="turn-title" className="turn">
      <h2 id="turn-title">Your turn</h2>
      {last && demand !== null && (
        <p className="banner">Last season you received {fmt(last.W)} of your {fmt(demand)} Mm³; harvest {fmt(last.Y, 0)} t; {signed(last.points)} points.</p>
      )}
      {left !== null && <p className="timer" aria-live="polite">{left} s</p>}
      <div className="pump-card">
        <p><strong>Borrow from the aquifer</strong></p>
        <div className="stepper" role="group" aria-label="Pump tokens">
          <button type="button" aria-label="One less" disabled={pumps <= 0 || pending} onClick={() => setPumps(p => p - 1)}>−</button>
          <output aria-valuetext={`${pumps} Mm³`} data-testid="pumps">{pumps}</output>
          <button type="button" aria-label="One more" disabled={pumps >= turn.options.length - 1 || pending} onClick={() => setPumps(p => p + 1)}>+</button>
        </div>
        <p>Pump cost at today's aquifer level: {fmt(turn.pumpCostPerMm3)} points per Mm³. The table will see how much was pumped, not by whom.</p>
        {option && <p data-testid="preview">Harvest {fmt(option.yieldT, 0)} t → {signed(points)} points</p>}
      </div>
      <div className="actions">
        <button type="button" aria-expanded={openActions} onClick={() => setOpenActions(o => !o)}>
          Actions: {Object.entries(turn.actions).map(([a, cost]) => `${ACTION_TEXT[a]?.name ?? a} ${cost}`).join(' · ') || 'none this season'}
        </button>
        {openActions && (
          <fieldset disabled={pending}>
            <legend>Play at most one action</legend>
            <label><input type="radio" name="action" checked={action === null} onChange={() => setAction(null)} /> No action</label>
            {Object.entries(turn.actions).map(([a, cost]) => (
              <label key={a}>
                <input type="radio" name="action" checked={action === a} onChange={() => setAction(a)} />
                {ACTION_TEXT[a]?.name ?? a} ({cost} points). {ACTION_TEXT[a]?.effect}
              </label>
            ))}
          </fieldset>
        )}
      </div>
      {pending
        ? <div className="toast" role="status">Committing… <button type="button" onClick={cancel}>Undo</button></div>
        : <button type="button" className="cta" onClick={commit}>Commit my turn</button>}
    </section>
  );
}
