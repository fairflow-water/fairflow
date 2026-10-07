# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Deployment settings. These are operational limits, not model parameters; each says where it comes from."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class Settings:
    # Browsers do not apply CORS to WebSocket handshakes, so the Origin header is checked against this list on every
    # connection (OWASP WebSocket Security Cheat Sheet: cross-site WebSocket hijacking). Empty means no browser may connect.
    allowed_origins: tuple[str, ...] = ()
    # OWASP WebSocket Security Cheat Sheet suggests capping messages around 64 KB; intents are a few hundred bytes.
    max_message_bytes: int = 64 * 1024
    # Per-connection token bucket (OWASP API4, unrestricted resource consumption): a burst, then a steady rate.
    rate_burst: int = 20
    rate_per_second: float = 5.0
    # Blueprint §7.1: "room codes (five characters)". The alphabet leaves out look-alikes (0/O, 1/I/L).
    room_code_length: int = 5
    room_code_alphabet: str = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    scenarios_dir: Path = field(default_factory=lambda: REPO / "packages" / "scenarios")
