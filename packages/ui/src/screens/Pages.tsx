// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// One page per kind of device: a player's phone, the facilitator (the Authority), and the projector. Each holds one
// connection and sees only its own projection; the facilitator and the projector see the public view only.
import QRCode from 'qrcode';
import { useEffect, useState } from 'react';
import { createRoom, roomInfo, tokenStore, type CreatedRoom } from '../api';
import type { PublicScenario } from '../room';
import { useRoom } from '../useRoom';
import { Join } from './Join';
import { Season } from './Season';

function useScenario(code: string): PublicScenario | null {
  const [scenario, setScenario] = useState<PublicScenario | null>(null);
  useEffect(() => { roomInfo(code).then(i => setScenario(i.scenario), () => setScenario(null)); }, [code]);
  return scenario;
}

function Live({ code, token, fallbackRole }: { code: string; token: string; fallbackRole: string }) {
  const scenario = useScenario(code);
  const room = useRoom(code, token);
  if (!scenario) return <p>Connecting…</p>;
  return (
    <>
      {room.notice && <p role="status" className="notice">{room.notice}</p>}
      <Season view={room.view} scenario={scenario} role={room.role ?? fallbackRole} onIntent={room.send} />
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

export function FacilitatorPage() {
  const [room, setRoom] = useState<CreatedRoom | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!room) {
    return (
      <main className="start">
        <h1>Fairflow</h1>
        <p>Open a room for your table. Participants join by scanning the QR code.</p>
        {error && <p role="alert" className="notice">The room could not be opened ({error}).</p>}
        <button type="button" className="cta" onClick={() => {
          createRoom('default-basin').then(setRoom, (e: unknown) => setError(e instanceof Error ? e.message : 'failed'));
        }}>Open a room</button>
      </main>
    );
  }
  const joinUrl = `${location.origin}${room.joinPath}`;
  return (
    <main>
      <header className="room-head">
        <h1>Room {room.room}</h1>
        <Qr text={joinUrl} />
        <a href={`/display/${room.room}#${room.displayToken}`} target="_blank" rel="noreferrer">Open the projector view</a>
      </header>
      <Live code={room.room} token={room.facilitatorToken} fallbackRole="authority" />
    </main>
  );
}

function Qr({ text }: { text: string }) {
  const [src, setSrc] = useState<string>('');
  useEffect(() => { QRCode.toDataURL(text, { margin: 1, width: 240 }).then(setSrc, () => setSrc('')); }, [text]);
  return src ? <img src={src} width={240} height={240} alt={`QR code to join: ${text}`} /> : null;
}
