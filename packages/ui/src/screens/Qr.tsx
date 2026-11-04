// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// A QR code for a link: the room's join link, or a one-time transfer link (ADR 0018). Drawn on the device; the link
// never leaves it. `label` is what the code is for, read out by screen readers.
import QRCode from 'qrcode';
import { useEffect, useState } from 'react';

export function Qr({ text, label = 'QR code to join' }: { text: string; label?: string }) {
  const [src, setSrc] = useState<string>('');
  useEffect(() => { QRCode.toDataURL(text, { margin: 1, width: 240 }).then(setSrc, () => setSrc('')); }, [text]);
  return src ? <img src={src} width={240} height={240} alt={`${label}: ${text}`} /> : null;
}
