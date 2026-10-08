// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S2 — joining a room from the QR code (blueprint §5.2, R3): consent comes first; nobody sees a role before it is given.
// The pre-session survey is not built yet, so the join records it as not done (review 2026-10-08, D6). The role token is stored on this device so a reload rejoins the same role.
import { useEffect, useState } from 'react';
import { deviceHash, joinRoom, roomInfo, tokenStore, type RoomInfo } from '../api';

export function Join({ code, onJoined }: { code: string; onJoined: (token: string) => void }) {
  const [info, setInfo] = useState<RoomInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);

  useEffect(() => {
    roomInfo(code).then(setInfo, (e: unknown) => setError(e instanceof Error ? e.message : 'unknown_room'));
  }, [code]);

  async function choose(role: string) {
    try {
      const token = await joinRoom(code, role, await deviceHash());
      tokenStore.set(code, token);
      onJoined(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'join_failed');
    }
  }

  if (error) return <p role="alert" className="notice">This room could not be joined ({error}).</p>;
  if (!info) return <p>Opening room {code}…</p>;
  const ready = consent;
  return (
    <section aria-labelledby="join-title" className="join">
      <h1 id="join-title">Room {info.room}</h1>
      <p>{info.scenario.name}</p>
      <p className="hint">The game records your farm, your decisions and a random code for this device. It does not ask for your name.</p>
      <label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /> I agree to take part.</label>
      {ready && (
        <>
          <h2>Choose your farm</h2>
          {info.freeRoles.length === 0 && <p>Every farm is taken.</p>}
          <ul className="roles">
            {info.scenario.schemes.filter(s => info.freeRoles.includes(s.id)).map(s => (
              <li key={s.id}><button type="button" onClick={() => void choose(s.id)}>{s.name}</button></li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
