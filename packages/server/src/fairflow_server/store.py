# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The room store (ADR 0012): one SQLite file on the server's own disk, so a restart does not end a game, and every room
is deleted a fixed time after its last move.

What is kept per room: the scenario it was opened on, the game's secret nonce, the record's events, the time of the last
event, and the SHA-256 of each role token (never a token itself: the tokens are bearer secrets, held only on the devices).
`secure_delete` overwrites deleted rows, and the rollback journal (not WAL) leaves no copy behind after a transaction, so
a deleted room is gone from the file, not only from the index."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    code TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    nonce TEXT NOT NULL,
    last_event REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    hash TEXT PRIMARY KEY,
    code TEXT NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
    role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    code TEXT NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    event TEXT NOT NULL,
    PRIMARY KEY (code, seq)
);
"""


@dataclass(frozen=True)
class StoredRoom:
    code: str
    scenario: dict[str, Any]
    nonce: str
    last_event: float
    tokens: dict[str, str]  # token hash → role
    events: list[dict[str, Any]]


class Store:
    """Writes are serialised by one lock: REST handlers run in a thread pool, WebSocket intents on the event loop."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        if new:
            path.chmod(0o600)  # owner only; Windows ignores all but the read-only bit
        self.lock = threading.Lock()
        for pragma in ("journal_mode = DELETE", "synchronous = FULL", "secure_delete = ON", "foreign_keys = ON"):
            self.db.execute(f"PRAGMA {pragma}")
        self.db.executescript(SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            self.db.execute("COMMIT")

    def create(self, code: str, scenario: dict[str, Any], nonce: str, at: float) -> None:
        with self._tx() as db:
            db.execute("INSERT INTO rooms VALUES (?, ?, ?, ?)", (code, json.dumps(scenario), nonce, at))

    def append(self, code: str, events: list[dict[str, Any]], at: float, tokens: list[tuple[str, str]]) -> None:
        """New events of one accepted intent, and any new tokens' hashes and roles, in one transaction."""
        with self._tx() as db:
            db.executemany(
                "INSERT INTO events VALUES (?, ?, ?)", [(code, e["seq"], json.dumps(e, sort_keys=True)) for e in events]
            )
            db.executemany("INSERT INTO tokens VALUES (?, ?, ?)", [(h, code, role) for h, role in tokens])
            db.execute("UPDATE rooms SET last_event = ? WHERE code = ?", (at, code))

    def exists(self, code: str) -> bool:
        with self.lock:
            return self.db.execute("SELECT 1 FROM rooms WHERE code = ?", (code,)).fetchone() is not None

    def delete(self, code: str) -> None:
        with self._tx() as db:
            db.execute("DELETE FROM rooms WHERE code = ?", (code,))

    def expired(self, before: float) -> list[str]:
        with self.lock:
            return [r[0] for r in self.db.execute("SELECT code FROM rooms WHERE last_event < ?", (before,))]

    def rooms(self) -> list[StoredRoom]:
        with self.lock:
            rows = self.db.execute("SELECT code, scenario, nonce, last_event FROM rooms").fetchall()
            out = []
            for code, scenario, nonce, last in rows:
                tokens = dict(self.db.execute("SELECT hash, role FROM tokens WHERE code = ?", (code,)).fetchall())
                events = [
                    json.loads(e)
                    for (e,) in self.db.execute("SELECT event FROM events WHERE code = ? ORDER BY seq", (code,))
                ]
                out.append(StoredRoom(code, json.loads(scenario), nonce, last, tokens, events))
            return out

    def close(self) -> None:
        with self.lock:
            self.db.close()
