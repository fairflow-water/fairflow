// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Routes: /                    facilitator opens a room
//         /join/{code}         participant (from the QR code)
//         /pre                 participant, the day before: the personal linking code (R3, ADR 0016, proposed)
//         /display/{code}#tok  projector; the token is in the fragment, which browsers never send to a server
import { DisplayPage, FacilitatorPage, PlayerPage } from './screens/Pages';
import { PreSession } from './screens/PreSession';

export function App() {
  const [, kind, code] = location.pathname.split('/');
  if (kind === 'join' && code) return <PlayerPage code={code.toUpperCase()} />;
  if (kind === 'pre') return <PreSession />;
  if (kind === 'display' && code) return <DisplayPage code={code.toUpperCase()} token={location.hash.slice(1)} />;
  return <FacilitatorPage />;
}
