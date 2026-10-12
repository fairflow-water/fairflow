// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
import { useEffect, useMemo, useRef, useState } from 'react';
import { connect, type LinkStatus, type RoomSocket } from './api';
import { applyMessage, viewOf, type RecordEvent, type RoomView } from './room';

export interface RoomConnection {
  view: RoomView;
  events: RecordEvent[];
  role: string | null;
  notice: string | null;
  link: LinkStatus | null; // null until the first connection opens
  send: (intent: Record<string, unknown>) => void;
  /** Like send, but silent: returns whether the intent went out, for a screen that retries by itself. */
  trySend: (intent: Record<string, unknown>) => boolean;
  /** How many full syncs the server has sent; each reconnection brings one. */
  syncs: number;
}

/** One WebSocket to the room for this device's token; every screen reads from the events it receives. */
export function useRoom(code: string, token: string | null): RoomConnection {
  const [events, setEvents] = useState<RecordEvent[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [link, setLink] = useState<LinkStatus | null>(null);
  const [syncs, setSyncs] = useState(0);
  const socket = useRef<RoomSocket | null>(null);

  useEffect(() => {
    if (!token) return undefined;
    const s = connect(code, token, msg => {
      if (msg.type === 'welcome') setRole(msg.role);
      else if (msg.type === 'rejected') setNotice(msg.message);
      else if (msg.type === 'invalid') setNotice('That action was not understood.');
      else {
        setNotice(null);
        setEvents(prev => applyMessage(prev, msg));
        if (msg.type === 'sync') setSyncs(n => n + 1);
      }
    }, setLink);
    socket.current = s;
    return () => s.close();
  }, [code, token]);

  const view = useMemo(() => viewOf(events), [events]);
  const trySend = (intent: Record<string, unknown>) => socket.current?.send(intent) ?? false;
  const send = (intent: Record<string, unknown>) => {
    if (!trySend(intent)) setNotice('Not connected just now, so that was not sent. Try again in a moment.');
  };
  return { view, events, role, notice, link, send, trySend, syncs };
}
