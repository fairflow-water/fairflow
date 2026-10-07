// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Routes: /                    facilitator opens a room
//         /join/{code}         participant (from the QR code)
//         /display/{code}#tok  projector; the token is in the fragment, which browsers never send to a server
import { DisplayPage, FacilitatorPage, PlayerPage } from './screens/Pages';

export function App() {
  const [, kind, code] = location.pathname.split('/');
  if (kind === 'join' && code) return <PlayerPage code={code.toUpperCase()} />;
  if (kind === 'display' && code) return <DisplayPage code={code.toUpperCase()} token={location.hash.slice(1)} />;
  return <FacilitatorPage />;
}
