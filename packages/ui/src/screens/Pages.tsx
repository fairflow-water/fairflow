// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// One page per kind of device: a player's phone, the facilitator (the Authority), and the projector. Each holds one
// connection and sees only its own projection; the facilitator and the projector see the public view only.
import { useCallback, useEffect, useState } from 'react';
import { claimTransfer, createRoom, deviceHash, hostStore, offerTransfer, roomInfo, tokenStore, type CreatedRoom } from '../api';
import type { PublicScenario } from '../room';
import { useRoom } from '../useRoom';
import { useWakeLock } from '../useWakeLock';
import { IDLE_RELEASE_MS, screenStaysOn, useIdle } from '../wakePolicy';
import { AuthorityCode, authorityLinkError, useAuthorityLink, type AuthorityLink } from './Handover';
import { Join } from './Join';
import { Qr } from './Qr';
import { Season } from './Season';

function useScenario(code: string): PublicScenario | null {
  const [scenario, setScenario] = useState<PublicScenario | null>(null);
  useEffect(() => { roomInfo(code).then(i => setScenario(i.scenario), () => setScenario(null)); }, [code]);
  return scenario;
}

function Live({ code, token, fallbackRole, authorityLink }: {
  code: string; token: string; fallbackRole: string; authorityLink?: AuthorityLink;
}) {
  const scenario = useScenario(code);
  const room = useRoom(code, token);
  useEffect(() => {
    if (room.link !== 'moved') return; // ADR 0018: this device's token no longer works; forget it here
    if (fallbackRole === 'authority') hostStore.remove(code);
    else tokenStore.leave(code, room.role ?? fallbackRole);
  }, [room.link, code, fallbackRole, room.role]);
  // E7, blueprint §5.4: the screen stays on for the session; after the game, until the form is sent or the device idles
  const idle = useIdle(room.view.phase === 'ended', IDLE_RELEASE_MS);
  useWakeLock(screenStaysOn({ link: room.link, phase: room.view.phase, review: room.view.review, idle }));
  if (!scenario) return <p>Connecting…</p>;
  return (
    <>
      {room.link === 'reconnecting' && <p role="status" className="notice">Connection lost. Reconnecting…</p>}
      {room.link === 'gone' && (
        <p role="alert" className="notice">This room is no longer on the server. Ask the facilitator.</p>
      )}
      {room.link === 'moved' && (
        <p role="alert" className="notice">This role now plays on another phone. You can close this page.</p>
      )}
      {room.notice && <p role="status" className="notice">{room.notice}</p>}
      <Season view={room.view} scenario={scenario} role={room.role ?? fallbackRole} onIntent={room.send}
        trySend={room.trySend} resync={room.syncs} clockOffsetMs={room.clockOffsetMs} events={room.events} code={code}
        {...(authorityLink ? { passAuthority: authorityLink } : {})} />
    </>
  );
}

export function PlayerPage({ code }: { code: string }) {
  const [token, setToken] = useState<string | null>(() => tokenStore.get(code));
  if (!token) return <Join code={code} onJoined={setToken} />;
  return <main><Live code={code} token={token} fallbackRole="player" /></main>;
}

export function DisplayPage({ code, token }: { code: string; token: string }) {
  const joinUrl = `${location.origin}/join/${code}`;
  return (
    <main className="display">
      <header><h1>Room {code}</h1><Qr text={joinUrl} /><p>{joinUrl}</p></header>
      <Live code={code} token={token} fallbackRole="display" />
    </main>
  );
}

// ADR 0018: after which season the Authority passes on: 1 up to the season before the shortest game's last, so that
// every game reaches it, or never (0)
const HANDOVER_CHOICES = [...Array.from({ length: __ROOM_SETTINGS__.shortestGame - 1 }, (_, i) => i + 1), 0];

export function FacilitatorPage() {
  const [room, setRoom] = useState<CreatedRoom | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hosted, setHosted] = useState<CreatedRoom[]>(() => hostStore.list());
  const [handover, setHandover] = useState<number>(__ROOM_SETTINGS__.authorityHandoverSeason); // the scenario's default

  function resume(r: CreatedRoom) {
    roomInfo(r.room).then(() => setRoom(r), () => {
      hostStore.remove(r.room);
      setHosted(hostStore.list());
      setError(`room ${r.room} is no longer on the server`);
    });
  }

  if (!room) {
    return (
      <main className="start">
        <h1>Fairflow</h1>
        <p>Open a room for your table. Participants join by scanning the QR code.</p>
        {error && (
          <p role="alert" className="notice">
            {error === 'bad_treatment' ? 'That hand-over season is outside the game. Choose another and open the room again.'
              : `The room could not be opened (${error}).`}
          </p>
        )}
        <label className="setting">
          Pass the Authority role to another student
          <select value={handover} onChange={e => setHandover(Number(e.target.value))}>
            {HANDOVER_CHOICES.map(n => <option key={n} value={n}>{n === 0 ? 'Never' : `After season ${n}`}</option>)}
          </select>
        </label>
        <button type="button" className="cta" onClick={() => {
          createRoom('default-basin', handover).then(r => { hostStore.add(r); setRoom(r); },
            (e: unknown) => setError(e instanceof Error ? e.message : 'failed'));
        }}>Open a room</button>
        {hosted.length > 0 && (
          <ul className="roles">
            {hosted.map(r => (
              <li key={r.room}><button type="button" onClick={() => resume(r)}>Continue room {r.room}</button></li>
            ))}
          </ul>
        )}
      </main>
    );
  }
  return <HostRoom room={room} />;
}

function HostRoom({ room }: { room: CreatedRoom }) {
  const code = room.room;
  const token = room.facilitatorToken;
  const makeLink = useCallback(
    () => offerTransfer(code, token, 'authority').then(link => `${location.origin}/transfer/${code}#${link}`), [code, token]);
  const authorityLink = useAuthorityLink(makeLink);
  const joinUrl = `${location.origin}${room.joinPath}`;
  return (
    <main>
      <header className="room-head">
        <h1>Room {room.room}</h1>
        <Qr text={joinUrl} />
        {room.displayToken && (
          <a href={`/display/${room.room}#${room.displayToken}`} target="_blank" rel="noreferrer">Open the projector view</a>
        )}
      </header>
      <Live code={code} token={token} fallbackRole="authority" authorityLink={authorityLink} />
      <MoveRole code={code} token={token} authorityLink={authorityLink} />
    </main>
  );
}

/** ADR 0018, issue #9: on the Authority's device, a one-time link (and QR code) that moves a role to another phone. */
function MoveRole({ code, token, authorityLink }: { code: string; token: string; authorityLink: AuthorityLink }) {
  const scenario = useScenario(code);
  const [shown, setShown] = useState<{ role: string; url: string } | 'authority' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ask = (role: string) => {
    setError(null);
    if (role === 'authority') { // the one Authority link, which the hand-over prompt shows too
      setShown('authority');
      authorityLink.make();
      return;
    }
    setShown(null); // never leave an older role's link on screen while a new one is made
    offerTransfer(code, token, role).then(
      link => setShown({ role, url: `${location.origin}/transfer/${code}#${link}` }),
      (e: unknown) => setError(e instanceof Error ? e.message : 'failed'));
  };
  if (!scenario) return null;
  return (
    <details className="move-role">
      <summary>Move a role to another phone</summary>
      <ul className="roles">
        {scenario.schemes.map(s => (
          <li key={s.id}><button type="button" onClick={() => ask(s.id)}>Move {s.name}</button></li>
        ))}
        <li><button type="button" onClick={() => ask('authority')}>Pass the Authority role</button></li>
      </ul>
      {error && (
        <p role="alert" className="notice">
          {error === 'not_seated' ? 'That irrigation scheme has no player yet.'
            : error === 'not_authority' ? 'This device no longer holds the Authority role.'
              : `The link could not be made (${error}).`}
        </p>
      )}
      {shown === 'authority' && authorityLink.url && <AuthorityCode url={authorityLink.url} />}
      {shown === 'authority' && authorityLink.error && (
        <p role="alert" className="notice">{authorityLinkError(authorityLink.error)}</p>
      )}
      {shown && shown !== 'authority' && (
        <div className="transfer-link" data-role={shown.role}>
          <p>Scan this with the new phone. The link works once; the old phone then stops.</p>
          <Qr text={shown.url} label="QR code to move a role" />
          <p>{shown.url}</p>
        </div>
      )}
    </details>
  );
}

/** ADR 0018, issue #9: the new phone claims the one-time link, keeps the role's token, and plays the role. The link
 * leaves the address once claimed, so a reload cannot try it again. */
const claims = new Map<string, Promise<{ token: string; role: string }>>(); // one claim per link, however often asked

export function TransferPage({ code, link }: { code: string; link: string }) {
  const [state, setState] = useState<{ role: string } | { error: string } | null>(null);
  useEffect(() => {
    let live = true;
    // A link works once: an effect that runs twice (React's StrictMode in development) must not claim it twice
    let claim = claims.get(link);
    if (!claim) {
      claim = deviceHash().then(device => claimTransfer(code, link, device));
      claims.set(link, claim);
    }
    claim.then(({ token, role }) => {
      if (role === 'authority') {
        hostStore.add({ room: code, facilitatorToken: token, displayToken: '', joinPath: `/join/${code}` });
        history.replaceState(null, '', '/');
      } else {
        tokenStore.set(code, token);
        history.replaceState(null, '', `/join/${code}`);
      }
      if (live) setState({ role });
    }, (e: unknown) => { if (live) setState({ error: e instanceof Error ? e.message : 'failed' }); });
    return () => { live = false; };
  }, [code, link]);
  if (state === null) return <main><p>Moving the role to this phone…</p></main>;
  if ('error' in state) {
    return (
      <main>
        <p role="alert" className="notice">
          {state.error === 'unknown_transfer'
            ? 'This link has been used or replaced. Ask the Authority for a new one.'
            : `The role could not be moved (${state.error}).`}
        </p>
      </main>
    );
  }
  return state.role === 'authority' ? <FacilitatorPage /> : <PlayerPage code={code} />;
}

