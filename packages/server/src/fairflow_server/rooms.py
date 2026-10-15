# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Rooms: one engine Game each, and the tokens that bind a connection to a role.

One process holds every room (the research brief found that sufficient for ~40 clients per room). With a store
(ADR 0012) each accepted intent is written to disk before anyone hears of it, so a restart resumes every game; without
one, rooms live in memory only. Either way a room is deleted `room_ttl_hours` after its last event."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fairflow_engine import AUTHORITY, Game, Rejection, audit, commitment, draw_secrets
from fairflow_engine.scenario import load_scenario

from .settings import Settings
from .store import Store, StoredRoom

log = logging.getLogger("fairflow.server")
DISPLAY = "display"  # the projector / shared screen: sees the public projection only


def _now() -> str:
    return datetime.now(UTC).isoformat()


def token_hash(token: str) -> str:
    """Rooms keep, and the store writes, only this hash of a role token (ADR 0012)."""
    return hashlib.sha256(token.encode()).hexdigest()


def load_registry(settings: Settings) -> dict[str, Any]:
    data = json.loads((settings.scenarios_dir / "parameters.json").read_text(encoding="utf-8"))
    return {p["key"]: p["default"] for p in data["parameters"]}


PUBLIC_SCHEME_FIELDS = ("id", "name", "seat", "shape", "glyph", "crop")


@dataclass
class Room:
    code: str
    game: Game
    scenario: dict[str, Any] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)  # token hash → role (AUTHORITY, a scheme id, or DISPLAY)
    last_event: float = 0.0  # wall-clock seconds of the last accepted event; the room is deleted a TTL after it

    def role_of(self, token: str) -> str | None:
        return self.tokens.get(token_hash(token))

    def public_scenario(self) -> dict[str, Any]:
        """What every screen may show about the basin: names, seats, shapes and lens plain names. No model numbers (the
        engine sends those in events) and nothing private."""
        return {
            "name": self.scenario.get("name"),
            "schemes": [{k: s[k] for k in PUBLIC_SCHEME_FIELDS if k in s} for s in self.scenario.get("schemes", [])],
            "session": self.scenario.get("session", {}),
            "lenses": [
                {"id": lens["id"], "plainName": lens.get("plainName", lens["id"])}
                for lens in self.scenario.get("lenses", [])
                if lens["enabled"]
            ],
        }

    def private_deadline(self, grace_default: float) -> tuple[int, float] | None:
        """ADR 0013: while a private turn is open, its season and the server's deadline (epoch seconds): the record time
        of the season's private.opened, plus the scenario's decisionS (the phone's deadline), plus the grace. None
        when no private turn is open or the scenario sets no decision time (then no side runs a timer)."""
        session = self.scenario.get("session", {})
        decision = session.get("decisionS")
        state = self.game.state
        if decision is None or state.phase != "private":
            return None
        opened = next(e for e in reversed(self.game.events) if e["type"] == "private.opened")
        start = datetime.fromisoformat(opened["t"]).timestamp()
        return opened["season"], start + decision + session.get("privateTurnGraceS", grace_default)

    def vote_deadline(self, last_short: int) -> tuple[int, float] | None:
        """ADR 0014: while a season's vote is open, its season and the server's negotiation deadline (epoch seconds): the
        record time of the season's season.climate (R7: "the negotiation timer starts when the lens screen opens") plus
        the scenario's negotiationS for that season (R20: "3:00 from screen open in seasons 0–2 and 4:00 from season
        3"; the registry's session.lastShortNegotiationSeason is the last short season). No grace: no client closes a
        vote by itself, so nothing has to be let in first. None when no vote is open or the scenario sets no
        negotiation time."""
        negotiation = self.scenario.get("session", {}).get("negotiationS")
        state = self.game.state
        if negotiation is None or state.phase != "vote":
            return None
        opened = next(e for e in reversed(self.game.events) if e["type"] == "season.climate")
        start = datetime.fromisoformat(opened["t"]).timestamp()
        length = negotiation["seasons0to2"] if opened["season"] <= last_short else negotiation["from3"]
        return opened["season"], start + length

    def free_roles(self) -> list[str]:
        taken = set(self.tokens.values())
        return [s.id for s in self.game.setup.schemes if s.id not in taken]


class RoomRegistry:
    def __init__(self, settings: Settings, now: Callable[[], float] = time.time):
        self.settings = settings
        self.now = now
        self.rooms: dict[str, Room] = {}
        self.registry = load_registry(settings)
        sheet = json.loads(settings.information_sheet.read_text(encoding="utf-8"))
        self.sheet_version: str = sheet["version"]
        stated = f"{settings.room_ttl_hours:g} hours"
        if sheet.get("roomTtlHours") != settings.room_ttl_hours or not any(stated in s["text"] for s in sheet["sections"]):
            raise RuntimeError(
                f"the information sheet must say rooms are kept {stated} after the last move (roomTtlHours and the "
                f"text), as the server is set (FAIRFLOW_ROOM_TTL_HOURS); it says {sheet.get('roomTtlHours')}"
            )
        if settings.research_enabled and settings.store_path is not None:
            raise RuntimeError(
                "research mode needs records kept for analysis (docs/plans/research-retention.md, not built); this "
                "store deletes every room after FAIRFLOW_ROOM_TTL_HOURS, so run it course-only"
            )
        self.store = Store(settings.store_path) if settings.store_path is not None else None
        if self.store is not None:
            for stored in self.store.rooms():
                self._restore(stored)

    @property
    def ttl_seconds(self) -> float:
        return self.settings.room_ttl_hours * 3600

    def _restore(self, stored: StoredRoom) -> None:
        """ADR 0012: a stored room is served again only if its record checks out: events numbered 1..n from
        game.created, the secrets drawn from the stored nonce match the commitments made at creation, and the engine
        recomputes every season. A room that fails is logged and not served; the sweep deletes it with the rest."""
        if stored.last_event + self.ttl_seconds < self.now():
            return
        try:
            load = load_scenario(stored.scenario, self.registry)
            if load.setup is None:
                raise ValueError("; ".join(load.errors))
            events = stored.events
            if [e["seq"] for e in events] != list(range(1, len(events) + 1)) or events[0]["type"] != "game.created":
                raise ValueError("the record is not numbered 1..n from game.created")
            sec = draw_secrets(load.setup, stored.nonce)
            made = events[0]["payload"]["commitments"]
            drawn = (commitment(sec.nonce, str(sec.T)), commitment(sec.nonce, ",".join(sec.deckOrder)))
            if drawn != (made["gameLength"], made["deckOrder"]):
                raise ValueError("the stored nonce does not reproduce the committed length and deck")
            problems = [p for p in audit(load.setup, events) if not p.startswith("note:")]
            if problems:
                raise ValueError("; ".join(problems))
            game = Game(load.setup, sec, events, _now)
            _ = game.state  # replays the record; raises if an event cannot be applied
        except (ValueError, KeyError, IndexError, TypeError) as e:
            log.warning("stored room set aside room=%s reason=%s", stored.code, e)
            return
        self.rooms[stored.code] = Room(stored.code, game, stored.scenario, dict(stored.tokens), stored.last_event)

    def _code(self) -> str:
        while True:
            code = "".join(secrets.choice(self.settings.room_code_alphabet) for _ in range(self.settings.room_code_length))
            if code not in self.rooms and not (self.store is not None and self.store.exists(code)):
                return code

    def record(self, room: Room, before: int, tokens: dict[str, str] | None = None) -> None:
        """Write what one accepted intent added (and any new token hashes) before anyone is told of it. If the write
        fails, the intent is undone in memory too, so memory and disk never disagree."""
        at = self.now()
        try:
            if self.store is not None:
                self.store.append(room.code, room.game.events[before:], at, list((tokens or {}).items()))
        except Exception:
            del room.game.events[before:]
            log.exception("store write failed room=%s", room.code)
            raise Rejection("storage_failed", "the move could not be saved; try again") from None
        room.tokens.update(tokens or {})
        room.last_event = at

    def create(self, scenario_id: str, server_version: str) -> tuple[Room, str, str]:
        """A new room on a shipped scenario. Returns the room, the facilitator's token (the Authority) and the
        display token."""
        path = (self.settings.scenarios_dir / f"{scenario_id}.json").resolve()
        if path.parent != self.settings.scenarios_dir.resolve() or not path.is_file():
            raise Rejection("unknown_scenario", scenario_id)
        scenario = json.loads(path.read_text(encoding="utf-8"))
        load = load_scenario(scenario, self.registry)
        if load.setup is None:
            raise Rejection("invalid_scenario", "; ".join(load.errors))
        code = self._code()
        nonce = secrets.token_hex(16)  # layout: 128-bit secret nonce, as the engine draws it; kept to resume the game
        game = Game.create(
            load.setup,
            code,
            "room",
            {"appVersion": server_version},
            _now,
            nonce=nonce,
            researchEnabled=self.settings.research_enabled,
        )
        room = Room(code, game, scenario)
        facilitator, display = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        room.game.submit(
            AUTHORITY,
            "join",
            deviceHash="facilitator",
            participationAcknowledged=True,
            researchConsent=None,
            infoSheetVersion=self.sheet_version,
            presurveyComplete=True,
        )
        if self.store is not None:
            self.store.create(code, scenario, nonce, self.now())
        self.record(room, 0, {token_hash(facilitator): AUTHORITY, token_hash(display): DISPLAY})
        self.rooms[code] = room
        return room, facilitator, display

    def join(
        self,
        code: str,
        role: str,
        device_hash: str,
        acknowledged: bool,
        research: bool | None,
        sheet: str,
        presurvey: bool,
    ) -> str:
        """R2–R3, ADR 0011: a free scheme role, recorded with part 1, the research answer (kept in a server-only
        event), the sheet version read and pre-survey status. Returns the role's token."""
        room = self.get(code)
        if role not in room.free_roles():
            raise Rejection("role_unavailable", role)
        if sheet != self.sheet_version:
            raise Rejection("stale_information_sheet", "reload the page to read the current information")
        before = len(room.game.events)
        room.game.submit(
            role,
            "join",
            deviceHash=device_hash,
            participationAcknowledged=acknowledged,
            researchConsent=research,
            infoSheetVersion=sheet,
            presurveyComplete=presurvey,
        )
        token = secrets.token_urlsafe(32)
        self.record(room, before, {token_hash(token): role})
        return token

    def get(self, code: str) -> Room:
        """A room past its TTL is deleted here, even before the sweep reaches it."""
        room = self.rooms.get(code.upper())
        if room is not None and room.last_event + self.ttl_seconds < self.now():
            self.delete(room.code)
            room = None
        if room is None:
            raise Rejection("unknown_room", code)
        return room

    def delete(self, code: str) -> None:
        self.rooms.pop(code, None)
        if self.store is not None:
            self.store.delete(code)
        log.info("room deleted room=%s", code)

    def sweep(self) -> list[str]:
        """ADR 0012: delete every room whose last event is older than the TTL, in memory and in the store (rooms set
        aside at start-up included). Returns their codes, so that their open connections can be closed."""
        cutoff = self.now() - self.ttl_seconds
        codes = {c for c, r in self.rooms.items() if r.last_event < cutoff}
        if self.store is not None:
            codes |= set(self.store.expired(cutoff))
        for code in sorted(codes):
            self.delete(code)
        return sorted(codes)
