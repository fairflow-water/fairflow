# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Rooms: one engine Game each, the tokens that bind a connection to a role, and the connections to broadcast to.

State is in memory (one process; the research brief found that sufficient for ~40 clients per room). Persistence and
EU-hosted storage of research records come with Tier 3 (DPIA, retention)."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fairflow_engine import AUTHORITY, Game, Rejection
from fairflow_engine.scenario import load_scenario

from .settings import Settings

DISPLAY = "display"  # the projector / shared screen: sees the public projection only


def _now() -> str:
    return datetime.now(UTC).isoformat()


def load_registry(settings: Settings) -> dict[str, Any]:
    data = json.loads((settings.scenarios_dir / "parameters.json").read_text(encoding="utf-8"))
    return {p["key"]: p["default"] for p in data["parameters"]}


PUBLIC_SCHEME_FIELDS = ("id", "name", "seat", "shape", "glyph", "crop")


@dataclass
class Room:
    code: str
    game: Game
    scenario: dict[str, Any] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)  # token → role (AUTHORITY, a scheme id, or DISPLAY)

    def public_scenario(self) -> dict[str, Any]:
        """What every screen may show about the basin: names, seats, shapes and lens plain names. No model numbers
        (the engine sends those in events) and nothing private."""
        return {
            "name": self.scenario.get("name"),
            "schemes": [{k: s[k] for k in PUBLIC_SCHEME_FIELDS if k in s} for s in self.scenario.get("schemes", [])],
            "lenses": [
                {"id": lens["id"], "plainName": lens.get("plainName", lens["id"])}
                for lens in self.scenario.get("lenses", [])
                if lens["enabled"]
            ],
        }

    def free_roles(self) -> list[str]:
        taken = set(self.tokens.values())
        return [s.id for s in self.game.setup.schemes if s.id not in taken]


class RoomRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.rooms: dict[str, Room] = {}
        self.registry = load_registry(settings)

    def _code(self) -> str:
        while True:
            code = "".join(secrets.choice(self.settings.room_code_alphabet) for _ in range(self.settings.room_code_length))
            if code not in self.rooms:
                return code

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
        room = Room(code, Game.create(load.setup, code, "room", {"appVersion": server_version}, _now), scenario)
        facilitator, display = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        room.game.submit(AUTHORITY, "join", deviceHash="facilitator", consentGiven=True, presurveyComplete=True)
        room.tokens[facilitator], room.tokens[display] = AUTHORITY, DISPLAY
        self.rooms[code] = room
        return room, facilitator, display

    def join(self, code: str, role: str, device_hash: str, consent: bool, presurvey: bool) -> str:
        """R2–R3: a free scheme role, recorded with consent and pre-survey status. Returns the role's token."""
        room = self.get(code)
        if role not in room.free_roles():
            raise Rejection("role_unavailable", role)
        room.game.submit(role, "join", deviceHash=device_hash, consentGiven=consent, presurveyComplete=presurvey)
        token = secrets.token_urlsafe(32)
        room.tokens[token] = role
        return token

    def get(self, code: str) -> Room:
        room = self.rooms.get(code.upper())
        if room is None:
            raise Rejection("unknown_room", code)
        return room
