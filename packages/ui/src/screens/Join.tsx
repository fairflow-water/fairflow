// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S2 — joining a room from the QR code (blueprint §5.2, R3): consent and the pre-survey come first; nobody sees a role
// before both are confirmed. The role token is stored on this device so a reload rejoins the same role.
import { useEffect, useState } from 'react';
import { deviceHash, joinRoom, roomInfo, tokenStore, type RoomInfo } from '../api';

export function Join({ code, onJoined }: { code: string; onJoined: (token: string) => void }) {
  const [info, setInfo] = useState<RoomInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [presurvey, setPresurvey] = useState(false);

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
  const ready = consent && presurvey;
  return (
    <section aria-labelledby="join-title" className="join">
      <h1 id="join-title">Room {info.room}</h1>
      <p>{info.scenario.name}</p>
      <label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /> I agree to take part.</label>
      <label><input type="checkbox" checked={presurvey} onChange={e => setPresurvey(e.target.checked)} /> I have answered the pre-session questions.</label>
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
