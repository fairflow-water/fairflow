// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S2 — joining a room from the QR code (blueprint §5.2, R3; ADR 0011). In order: the information (content/information-
// sheet.json), part 1 (taking part, required), part 2 (research, yes or no, nothing pre-selected; only when the
// deployment enables research), then the scheme. Nobody sees a scheme before part 1 is given; the research answer is sent
// to the server, which keeps it from every screen. The pre-session survey is not built yet, so the join records it as
// not done (review 2026-10-08, D6). The role token is stored on this device so a reload rejoins the same role.
import { useEffect, useState } from 'react';
import sheet from '../../../../content/information-sheet.json';
import { deviceHash, joinRoom, roomInfo, tokenStore, type RoomInfo } from '../api';
import { linkingStore } from '../linking';

export function Join({ code, onJoined }: { code: string; onJoined: (token: string) => void }) {
  const [info, setInfo] = useState<RoomInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [taking, setTaking] = useState(false);
  const [research, setResearch] = useState<boolean | null>(null);
  const [linkingCode] = useState(() => linkingStore.get()); // made before the session on this phone (R3)
  const [duplicate, setDuplicate] = useState(false); // ADR 0016: the join was refused for a code already given

  useEffect(() => {
    roomInfo(code).then(setInfo, (e: unknown) => setError(e instanceof Error ? e.message : 'unknown_room'));
  }, [code]);

  const asked = info?.researchEnabled === true;

  async function choose(role: string) {
    try {
      const { token } = await joinRoom(code, role, await deviceHash(),
        { infoSheetVersion: sheet.version, researchConsent: asked ? research : null }, linkingCode);
      tokenStore.set(code, token);
      onJoined(token);
    } catch (e) {
      if (e instanceof Error && e.message === 'duplicate_linking_code') {
        linkingStore.clear(); // ADR 0016: no join under a code already given; a new one is made on /pre
        setDuplicate(true);
      } else setError(e instanceof Error ? e.message : 'join_failed');
    }
  }

  if (error) return <p role="alert" className="notice">This room could not be joined ({error}).</p>;
  if (!info) return <p>Opening room {code}…</p>;
  if (duplicate) {
    return (
      <section aria-labelledby="join-title" className="join">
        <h1 id="join-title">Room {info.room}</h1>
        {/* the maintainer, 2026-10-15: only this; it does not say that anyone else holds the code */}
        <p role="status" className="notice">Choose a different code.</p>
        <p><a href="/pre">Make a different code</a></p>
      </section>
    );
  }
  const needsCode = asked && !linkingCode; // ADR 0016: a code is required while research is enabled
  const ready = taking && (!asked || research !== null) && !needsCode;
  return (
    <section aria-labelledby="join-title" className="join">
      <h1 id="join-title">Room {info.room}</h1>
      <p>{info.scenario.name}</p>
      {linkingCode && <p className="hint">Your linking code, made before the session, goes with your join: {linkingCode}</p>}
      <p className="hint">{sheet.summary}{asked && <> {sheet.summaryResearch}</>}</p>
      <details className="information-sheet">
        <summary>{sheet.title}</summary>
        {sheet.sections.filter(s => asked || !s.research).map(s => (
          <p key={s.heading}><strong>{s.heading}.</strong> {s.text}</p>
        ))}
      </details>
      <label><input type="checkbox" checked={taking} onChange={e => setTaking(e.target.checked)} /> {sheet.part1}</label>
      {asked && (
        <fieldset>
          <legend>{sheet.part2}</legend>
          <label><input type="radio" name="research" checked={research === true} onChange={() => setResearch(true)} /> Yes</label>
          <label><input type="radio" name="research" checked={research === false} onChange={() => setResearch(false)} /> No</label>
          <p className="hint">To withdraw later you need the room code ({info.room}), your scheme and today’s date; the game shows them again at the end.</p>
        </fieldset>
      )}
      {needsCode && taking && research !== null && (
        <p className="notice">This session links survey answers by a code you make yourself. <a href="/pre">Make your
          personal linking code first</a>, on this phone, then come back to this page.</p>
      )}
      {ready && (
        <>
          <h2>Choose your irrigation scheme</h2>
          {info.freeRoles.length === 0 && <p>Every irrigation scheme is taken.</p>}
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
