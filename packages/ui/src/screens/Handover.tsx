// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0018 decision 2: at the reveal of the room's hand-over season, the Authority's device asks to pass the role to
// the next student. One tap makes the one-time link and shows it as a QR code; the new phone scans it and becomes the
// Authority, and this device is told the role has moved. Opening the next season instead keeps the role here.
//
// The server keeps one live link per role: a newer one replaces the older. So the Authority's device keeps one
// Authority link, shared by this prompt and the "Move a role" panel: wherever it is made, both show the same code,
// and no screen is left showing a replaced one.
import { useCallback, useRef, useState } from 'react';
import { Qr } from './Qr';

export type AuthorityLink = {
  /** The current one-time link, once made. */
  url: string | null;
  /** Why the last attempt failed: a server code, or 'failed'. */
  error: string | null;
  /** Makes a new link, which replaces any older one. */
  make: () => void;
};

export function useAuthorityLink(makeLink: () => Promise<string>): AuthorityLink {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(0); // only the newest request may fill the screen: the server keeps the link it made last
  const make = useCallback(() => {
    const mine = ++latest.current;
    setError(null);
    setUrl(null); // the older link is replaced on the server, so never leave it on screen while the new one is made
    makeLink().then(
      u => { if (mine === latest.current) setUrl(u); },
      (e: unknown) => { if (mine === latest.current) setError(e instanceof Error ? e.message : 'failed'); });
  }, [makeLink]);
  return { url, error, make };
}

export const authorityLinkError = (error: string): string =>
  error === 'not_authority' ? 'This device no longer holds the Authority role.' : `The code could not be made (${error}). Try again.`;

export function AuthorityCode({ url }: { url: string }) {
  return (
    <div className="transfer-link" data-role="authority">
      <p>The next Authority scans this code with their phone. It works once; this device then stops.</p>
      <Qr text={url} label="QR code to become the Authority" />
      <p>{url}</p>
    </div>
  );
}

export function HandoverPrompt({ season, link }: { season: number; link: AuthorityLink }) {
  return (
    <section aria-labelledby="handover-title" className="card handover">
      <h2 id="handover-title">Pass the Authority role</h2>
      <p>Season {season} is over. The next student becomes the Authority now, before season {season + 1} opens.</p>
      {link.url === null
        ? <button type="button" className="cta" onClick={link.make}>Show the code for the next Authority</button>
        : <AuthorityCode url={link.url} />}
      {link.error && <p role="alert" className="notice">{authorityLinkError(link.error)}</p>}
      <p className="hint">To keep the role on this device, open the next season.</p>
    </section>
  );
}
