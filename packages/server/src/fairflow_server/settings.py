# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Deployment settings. These are operational limits, not model parameters; each says where it comes from."""

from __future__ import annotations

import os
from collections.abc import Mapping
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
    # ADR 0011: the information sheet shown at join; a join must name the version this server serves.
    information_sheet: Path = field(default_factory=lambda: REPO / "content" / "information-sheet.json")
    # ADR 0011: course-only (no research question) unless the deployment enables research, which it should do only
    # once the sheet's placeholders are filled and ethics approval is given.
    research_enabled: bool = False
    # ADR 0012: the room store, one SQLite file on this server's own disk; None keeps rooms in memory only (development
    # and tests), so a restart ends every game.
    store_path: Path | None = None
    # ADR 0012: a room, with its whole record, is deleted this long after its last event. The information sheet states
    # the same period ("roomTtlHours"); the server refuses to start if they differ.
    room_ttl_hours: float = 24.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str] = os.environ) -> Settings:
        """Deployment configuration: FAIRFLOW_ALLOWED_ORIGINS is a comma-separated list of browser origins (e.g. the
        site's own https origin; http://localhost:5173 for development). Unset means no browser may connect.
        FAIRFLOW_RESEARCH_ENABLED=1 asks every scheme the research question (ADR 0011); anything else is course-only.
        FAIRFLOW_STORE is the path of the room store's file (ADR 0012); unset keeps rooms in memory. FAIRFLOW_ROOM_TTL_HOURS
        is how long a room is kept after its last event (default 24)."""
        raw = environ.get("FAIRFLOW_ALLOWED_ORIGINS", "")
        store = environ.get("FAIRFLOW_STORE", "")
        ttl = environ.get("FAIRFLOW_ROOM_TTL_HOURS", "")
        return cls(
            allowed_origins=tuple(o.strip() for o in raw.split(",") if o.strip()),
            research_enabled=environ.get("FAIRFLOW_RESEARCH_ENABLED", "") == "1",
            store_path=Path(store) if store else None,
            room_ttl_hours=float(ttl) if ttl else cls.room_ttl_hours,
        )
