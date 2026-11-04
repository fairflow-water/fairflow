// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Routes: /                    facilitator opens a room
//         /join/{code}         participant (from the QR code)
//         /display/{code}#tok  projector; the token is in the fragment, which browsers never send to a server
//         /transfer/{code}#link a role moved to this phone (ADR 0018); the one-time link is in the fragment too
import { DisplayPage, FacilitatorPage, PlayerPage, TransferPage } from './screens/Pages';

export function App() {
  const [, kind, code] = location.pathname.split('/');
  if (kind === 'join' && code) return <PlayerPage code={code.toUpperCase()} />;
  if (kind === 'display' && code) return <DisplayPage code={code.toUpperCase()} token={location.hash.slice(1)} />;
  if (kind === 'transfer' && code) return <TransferPage code={code.toUpperCase()} link={location.hash.slice(1)} />;
  return <FacilitatorPage />;
}
