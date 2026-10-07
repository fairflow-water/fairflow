# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The client → server message protocol, validated strictly (OWASP: validate untrusted input; unknown fields are errors).

A message names an intent and its arguments, never the actor: who acts is the role bound to the connection's token
(OWASP API1/API5 — a client cannot act as another role by putting a different name in the message)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

Finite = Annotated[float, Field(allow_inf_nan=False)]


class _Intent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    def args(self) -> dict[str, Any]:
        return self.model_dump(exclude={"intent"}, exclude_none=True)


class StartSeason(_Intent):
    intent: Literal["start_season"]


class Propose(_Intent):
    intent: Literal["propose"]
    lens: str


class Vote(_Intent):
    intent: Literal["vote"]
    lens: str


class CloseVote(_Intent):
    intent: Literal["close_vote"]


class BreakTie(_Intent):
    intent: Literal["break_tie"]
    lens: str


class FloorVote(_Intent):
    intent: Literal["floor_vote"]
    rule: str


class CloseFloorVote(_Intent):
    intent: Literal["close_floor_vote"]
    tieBreak: str | None = None


class Commit(_Intent):
    """R10: pump tokens and at most one Module 1 action token."""

    intent: Literal["commit"]
    pumps: Finite
    action: Literal["orchard", "drip", "expand"] | None = None


class Timebox(_Intent):
    intent: Literal["timebox"]
    sessionMinute: Finite


class OpenDebrief(_Intent):
    intent: Literal["open_debrief"]
    perPlayer: bool


Intent = Annotated[
    StartSeason | Propose | Vote | CloseVote | BreakTie | FloorVote | CloseFloorVote | Commit | Timebox | OpenDebrief,
    Field(discriminator="intent"),
]
INTENT: TypeAdapter[Intent] = TypeAdapter(Intent)


class JoinRequest(BaseModel):
    """POST /rooms/{code}/join. deviceHash is a client-side salted hash, never a device identifier (blueprint §6.2)."""

    model_config = ConfigDict(extra="forbid", strict=True)
    role: str
    deviceHash: Annotated[str, Field(min_length=8, max_length=128)]
    consentGiven: bool
    presurveyComplete: bool
