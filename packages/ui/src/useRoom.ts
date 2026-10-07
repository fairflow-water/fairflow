// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
import { useEffect, useMemo, useRef, useState } from 'react';
import { connect, type RoomSocket } from './api';
import { applyMessage, viewOf, type RecordEvent, type RoomView } from './room';

export interface RoomConnection {
  view: RoomView;
  events: RecordEvent[];
  role: string | null;
  notice: string | null;
  send: (intent: Record<string, unknown>) => void;
}

/** One WebSocket to the room for this device's token; every screen reads from the events it receives. */
export function useRoom(code: string, token: string | null): RoomConnection {
  const [events, setEvents] = useState<RecordEvent[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const socket = useRef<RoomSocket | null>(null);

  useEffect(() => {
    if (!token) return undefined;
    const s = connect(code, token, msg => {
      if (msg.type === 'welcome') setRole(msg.role);
      else if (msg.type === 'rejected') setNotice(msg.message);
      else if (msg.type === 'invalid') setNotice('That action was not understood.');
      else { setNotice(null); setEvents(prev => applyMessage(prev, msg)); }
    });
    socket.current = s;
    return () => s.close();
  }, [code, token]);

  const view = useMemo(() => viewOf(events), [events]);
  return { view, events, role, notice, send: intent => socket.current?.send(intent) };
}
