// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S6 — the private turn (blueprint §5.2, R10, R20). This scheme's last results, a 0–cap pump stepper framed as borrowing,
// the action tokens collapsed to one line, and the engine's preview of harvest and points for the current choice.
// The countdown runs to the server's deadline, the record time of private.opened plus the scenario's decision time, on
// the server's clock (ADR 0013), so a reload continues it; at zero it commits the current choice, marked as the phone's
// timer. The server commits the untouched default a grace later for a phone that never does. A commit can be undone for
// 3 s. Every number comes from the engine's private.opened and season.resolved events.
// A commit is final on this phone once sent, but it counts only when the server records it: if it could not be sent
// (no connection), or the connection died with it, the turn stays open and the same choice is sent again, with the same
// timer mark, after the server's next full sync, which every reconnection brings. A sync that still shows this turn open
// means the server holds no commit from this phone (once it does, this screen is replaced).
import { useEffect, useRef, useState } from 'react';
import type { MyResult, PrivateTurn as Turn } from '../room';

const UNDO_MS = 3000; // §5.2 S6 "hold-to-commit with 3 s undo"
const MS = 1000; // layout: milliseconds per second
const TICK_MS = 250; // layout: how often the countdown is redrawn
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
  clockOffsetMs?: number; // the server's clock minus this device's (ADR 0013)
  /** Returns false when the commit could not be sent (no connection). */
  onCommit: (pumps: number, action: string | null, byTimeout: boolean) => boolean;
  /** Counts the server's full syncs; a new one while this turn is open re-sends a commit made here. */
  resync?: number | undefined;
}

export function PrivateTurn({ turn, last, demand, decisionS, clockOffsetMs = 0, onCommit, resync }: PrivateTurnProps) {
  const [level, setLevel] = useState(0); // index into the engine's offered pump levels (ADR 0008: the last may be fractional)
  const pumps = turn.options[level]?.pumps ?? 0;
  const [action, setAction] = useState<string | null>(null);
  const [openActions, setOpenActions] = useState(false);
  const [pending, setPending] = useState(false);
  const [left, setLeft] = useState<number | null>(decisionS);
  const choice = useRef({ pumps, action });
  choice.current = { pumps, action };
  const undo = useRef<ReturnType<typeof setTimeout> | null>(null);
  const made = useRef<{ pumps: number; action: string | null; byTimeout: boolean } | null>(null); // the commit made on this phone
  const [delivery, setDelivery] = useState<'none' | 'sent' | 'waiting'>('none');

  const send = (p: number, a: string | null, byTimeout = false) => {
    if (made.current) return;
    made.current = { pumps: p, action: a, byTimeout };
    setPending(true);
    setDelivery(onCommit(p, a, byTimeout) ? 'sent' : 'waiting');
  };

  useEffect(() => {
    if (!made.current) return;
    setDelivery(onCommit(made.current.pumps, made.current.action, made.current.byTimeout) ? 'sent' : 'waiting');
  }, [resync]);

  useEffect(() => {
    if (decisionS === null) return undefined;
    // ADR 0013: the deadline is on the server's clock; without the record time (a test fixture) it runs from now
    const opened = turn.openedAt === undefined ? Number.NaN : Date.parse(turn.openedAt);
    const deadline = (Number.isNaN(opened) ? Date.now() + clockOffsetMs : opened) + decisionS * MS;
    const update = () => {
      const remaining = Math.max(0, Math.ceil((deadline - (Date.now() + clockOffsetMs)) / MS));
      setLeft(remaining);
      if (remaining === 0) {
        clearInterval(tick);
        send(choice.current.pumps, choice.current.action, true); // R20: auto-commit the current choice
      }
    };
    const tick = setInterval(update, TICK_MS);
    update();
    return () => clearInterval(tick);
  }, [decisionS, turn.openedAt, clockOffsetMs]);

  useEffect(() => () => { if (undo.current) clearTimeout(undo.current); }, []);

  const option = turn.options[level] ?? turn.options[0];
  const points = option?.points ? option.points[action ?? 'none'] ?? option.points['none'] ?? 0 : 0;

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
        <p className="banner">Last season you used {fmt(last.W)} Mm³ (allocated + pumped), {fmt(last.A * 100, 0)} % of what you needed; harvest {fmt(last.Y, 0)} t; {signed(last.points)} points.</p>
      )}
      {left !== null && <p className="timer" aria-live="polite">{left} s</p>}
      <div className="pump-card">
        <p><strong>Borrow from the aquifer</strong></p>
        <div className="stepper" role="group" aria-label="Pump tokens">
          <button type="button" aria-label="One less" disabled={level <= 0 || pending} onClick={() => setLevel(l => l - 1)}>−</button>
          <output aria-valuetext={`${fmt(pumps)} Mm³`} data-testid="pumps">{fmt(pumps)}</output>
          <button type="button" aria-label="One more" disabled={level >= turn.options.length - 1 || pending} onClick={() => setLevel(l => l + 1)}>+</button>
        </div>
        {turn.wellsDry && <p className="notice" role="status">Your wells are dry: the water table has fallen below what your pumps can lift, so you cannot pump this season.</p>}
        {!turn.wellsDry && <p>Your wells can deliver up to {fmt(turn.cap)} Mm³ this season.</p>}
        <p>Pump cost at today's aquifer level: {fmt(turn.pumpCostPerMm3)} points per Mm³. During play the table sees only the total pumped, though others may be able to work out part of it from the total. At the debrief the facilitator may show each scheme's pumping.</p>
        {option && option.yieldT !== null && <p data-testid="preview">Harvest {fmt(option.yieldT, 0)} t → {signed(points)} points</p>}
        {option && option.yieldT === null && (
          <p data-testid="preview">Above {fmt(turn.previewLimit ?? 0)} Mm³ your wells may run short: what you get then depends on the stock and on what the others pump.</p>
        )}
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
      {delivery === 'waiting' && (
        <div className="toast" role="status">Not connected. Your turn is kept and will be sent when the connection is back.</div>
      )}
      {delivery === 'sent' && <div className="toast" role="status">Sending your turn…</div>}
      {delivery === 'none' && (pending
        ? <div className="toast" role="status">Committing… <button type="button" onClick={cancel}>Undo</button></div>
        : <button type="button" className="cta" onClick={commit}>Commit my turn</button>)}
    </section>
  );
}
