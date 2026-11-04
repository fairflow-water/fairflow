// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0018 decision 2: at the reveal of the room's hand-over season, the Authority's device asks to pass the role to
// the next student. One tap makes the one-time link and shows it as a QR code; the new phone scans it and becomes the
// Authority, and this device is told the role has moved. Opening the next season instead keeps the role here.
import { useState } from 'react';
import { Qr } from './Qr';

export function HandoverPrompt({ season, makeLink }: { season: number; makeLink: () => Promise<string> }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const show = () => {
    setError(null);
    makeLink().then(setUrl, (e: unknown) => setError(e instanceof Error ? e.message : 'failed'));
  };
  return (
    <section aria-labelledby="handover-title" className="card handover">
      <h2 id="handover-title">Pass the Authority role</h2>
      <p>Season {season} is over. The next student becomes the Authority now, before season {season + 1} opens.</p>
      {url === null
        ? <button type="button" className="cta" onClick={show}>Show the code for the next Authority</button>
        : (
          <div className="transfer-link" data-role="authority">
            <p>The next Authority scans this code with their phone. It works once.</p>
            <Qr text={url} label="QR code to become the Authority" />
            <p>{url}</p>
          </div>
        )}
      {error && (
        <p role="alert" className="notice">
          {error === 'not_authority' ? 'This device no longer holds the Authority role.' : `The code could not be made (${error}). Try again.`}
        </p>
      )}
      <p className="hint">To keep the role on this device, open the next season.</p>
    </section>
  );
}
