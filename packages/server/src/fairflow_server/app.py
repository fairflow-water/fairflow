# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""FastAPI room server (ADR 0002). REST to create and join rooms; one WebSocket per device for intents and projections.

Security choices (OWASP API Security Top 10 2023; OWASP WebSocket Security Cheat Sheet):
- the acting role comes from the connection's token, never from a message (API1/API5);
- the token is sent as the first WebSocket message, not in the URL, so it does not land in access logs;
- the Origin header is checked against an allowlist on every handshake (cross-site WebSocket hijacking);
- every message is size-capped, rate-limited per connection (API4) and validated strictly (unknown fields rejected);
- each connection receives only its own role's projection: sealed data never leave the server before the debrief;
- logs carry room, role and intent type only — no device hashes, tokens or free text — and no client IP address:
  uvicorn logs each WebSocket handshake with the client's address even with --no-access-log, so that address is
  blanked here (`NoClientAddress`), whatever the log level (ADR 0012);
- with a store (ADR 0012), each accepted intent is on disk before it is broadcast, and a room is deleted
  `room_ttl_hours` after its last event, its connections closed.

The private turn is timed here (ADR 0013): when its deadline plus a grace has passed, the engine commits the untouched
default for every scheme that has not committed, so a season resolves when a phone is gone.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Any

from fairflow_engine import ENGINE, Rejection, project
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, ValidationError

from .protocol import INTENT, JoinRequest
from .rooms import DISPLAY, Room, RoomRegistry
from .settings import Settings

log = logging.getLogger("fairflow.server")
SERVER_VERSION = "1.0.0.dev0"
POLICY_VIOLATION = 1008  # RFC 6455 close codes (layout)
MESSAGE_TOO_BIG = 1009
SWEEP_EVERY_S = 600.0  # layout: how often expired rooms are looked for; `get` refuses an expired room at once anyway
TIMER_TICK_S = 1.0  # layout: how often a private-turn timer reads the clock (seconds)
MS = 1000  # layout: the welcome message gives the server's time in milliseconds, as the browser counts it


class CreateRoom(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    scenario: str


@dataclass
class TokenBucket:
    """Per-connection rate limit: `burst` messages at once, refilled at `rate` per second."""

    burst: int
    rate: float
    tokens: float = 0.0
    stamp: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        self.tokens = float(self.burst)

    def take(self) -> bool:
        now = time.monotonic()
        self.tokens = min(float(self.burst), self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


@dataclass
class Connection:
    socket: WebSocket
    role: str
    last_seq: int = 0


class NoClientAddress(logging.Filter):
    """Blank the client address uvicorn puts first in its WebSocket handshake lines ('%s - "WebSocket %s" …')."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and record.msg.startswith('%s - "WebSocket') and isinstance(record.args, tuple):
            record.args = ("-", *record.args[1:])
        return True


def _viewer(role: str) -> str:
    return "public" if role == DISPLAY else role


def create_app(settings: Settings | None = None, now: Callable[[], float] = time.time) -> FastAPI:
    """`now` is the wall clock the room TTL and the private-turn deadline are measured on (a test passes its own)."""
    settings = settings or Settings.from_env()
    uvicorn_log = logging.getLogger("uvicorn.error")
    if not any(isinstance(f, NoClientAddress) for f in uvicorn_log.filters):
        uvicorn_log.addFilter(NoClientAddress())
    registry = RoomRegistry(settings, now)
    grace_default: float = registry.registry["session.privateTurnGraceS"]  # ADR 0013
    connections: dict[str, list[Connection]] = {}
    locks: dict[str, asyncio.Lock] = {}
    timers: dict[str, asyncio.Task[None]] = {}  # room code → the open private turn's timer

    async def sweep() -> None:
        for code in registry.sweep():
            locks.pop(code, None)
            for conn in connections.pop(code, []):
                with suppress(RuntimeError, WebSocketDisconnect):
                    await conn.socket.close(code=POLICY_VIOLATION)  # the client shows the room as gone

    async def sweeper() -> None:
        while True:
            await sweep()
            await asyncio.sleep(SWEEP_EVERY_S)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(sweeper())
        try:
            yield
        finally:
            for t in [task, *timers.values()]:
                t.cancel()
                with suppress(asyncio.CancelledError):
                    await t
            if registry.store is not None:
                registry.store.close()

    app = FastAPI(title="Fairflow room server", version=SERVER_VERSION, lifespan=lifespan)
    app.state.registry = registry
    app.state.sweep = sweep
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_methods=["GET", "POST"], allow_headers=["*"]
    )

    def http_error(e: Rejection) -> HTTPException:
        status = 404 if e.code in ("unknown_room", "unknown_scenario") else 503 if e.code == "storage_failed" else 409
        return HTTPException(status_code=status, detail={"code": e.code, "message": str(e)})

    @app.post("/rooms")
    def create_room(body: CreateRoom) -> dict[str, str]:
        try:
            room, facilitator, display = registry.create(body.scenario, SERVER_VERSION)
        except Rejection as e:
            raise http_error(e) from None
        log.info("room created room=%s", room.code)
        return {
            "room": room.code,
            "facilitatorToken": facilitator,
            "displayToken": display,
            "joinPath": f"/join/{room.code}",
        }

    @app.get("/rooms/{code}")
    def room_info(code: str) -> dict[str, Any]:
        try:
            room = registry.get(code)
        except Rejection as e:
            raise http_error(e) from None
        return {
            "room": room.code,
            "freeRoles": room.free_roles(),
            "phase": room.game.state.phase,
            "scenario": room.public_scenario(),
            "researchEnabled": room.game.state.researchEnabled,  # ADR 0011: whether S2 asks the research question
            "infoSheetVersion": registry.sheet_version,
        }

    @app.post("/rooms/{code}/join")
    async def join(code: str, body: JoinRequest) -> dict[str, str]:
        # Under the room's lock, like every intent, and broadcast, so the lobby sees who has joined.
        try:
            room = registry.get(code)
        except Rejection as e:
            raise http_error(e) from None
        async with locks.setdefault(room.code, asyncio.Lock()):
            before = len(room.game.events)
            try:
                token = registry.join(
                    code,
                    body.role,
                    body.deviceHash,
                    body.participationAcknowledged,
                    body.researchConsent,
                    body.infoSheetVersion,
                    body.presurveyComplete,
                )
            except Rejection as e:
                raise http_error(e) from None
            log.info("joined room=%s role=%s", room.code, body.role)
            await broadcast(room, before)
        return {"token": token, "role": body.role}

    async def send_projection(room: Room, conn: Connection, full: bool) -> None:
        events = project(room.game.events, _viewer(conn.role))
        if full:
            await conn.socket.send_json({"type": "sync", "events": events})
        else:
            # Sent after every accepted intent, empty when nothing new is visible to this viewer: it says that something
            # happened (e.g. "a player committed"), never what or by whom, and keeps every client in step.
            fresh = [e for e in events if e["seq"] > conn.last_seq]
            await conn.socket.send_json({"type": "events", "events": fresh})
        if events:
            conn.last_seq = max(e["seq"] for e in events)

    async def broadcast(room: Room, before: int) -> None:
        new = room.game.events[before:]
        full = any(e["type"] == "debrief.opened" for e in new)  # the debrief re-projects earlier sealed events
        for conn in list(connections.get(room.code, [])):
            try:
                await send_projection(room, conn, full)
            except (WebSocketDisconnect, RuntimeError):
                connections[room.code].remove(conn)
        arm(room)

    def arm(room: Room) -> None:
        """Start the timer of a private turn that has just opened (one per season; called after every change)."""
        due = room.private_deadline(grace_default)
        if due is None:
            return
        season, deadline = due
        name = f"{room.code}:{season}"
        running = timers.get(room.code)
        if running is not None and not running.done() and running.get_name() == name:
            return
        timers[room.code] = asyncio.create_task(expire(room, season, deadline), name=name)

    async def expire(room: Room, season: int, deadline: float) -> None:
        """ADR 0013: at the server's deadline, commit the untouched default for every scheme still missing."""
        while (left := deadline - now()) > 0:
            await asyncio.sleep(min(left, TIMER_TICK_S))
        async with locks.setdefault(room.code, asyncio.Lock()):
            state = room.game.state
            if state.phase != "private" or state.season != season:
                return  # every scheme committed in time
            before = len(room.game.events)
            try:
                room.game.submit(ENGINE, "timeout_private", season=season)
            except Rejection as r:
                log.warning("timer refused room=%s code=%s", room.code, r.code)
                return
            log.info("accepted room=%s role=%s intent=%s", room.code, ENGINE, "timeout_private")
            await broadcast(room, before)

    @app.websocket("/rooms/{code}/ws")
    async def socket(websocket: WebSocket, code: str) -> None:
        if websocket.headers.get("origin") not in settings.allowed_origins:
            await websocket.close(code=POLICY_VIOLATION)
            return
        await websocket.accept()
        try:
            room = registry.get(code)
            first = await websocket.receive_text()
            if len(first.encode()) > settings.max_message_bytes:
                await websocket.close(code=MESSAGE_TOO_BIG)
                return
            auth = json.loads(first)
            token = auth.get("token") if isinstance(auth, dict) else None
            role = room.role_of(token) if isinstance(token, str) else None
        except (Rejection, json.JSONDecodeError):
            role = None
        if role is None:
            await websocket.close(code=POLICY_VIOLATION)
            return
        conn = Connection(websocket, role)
        connections.setdefault(room.code, []).append(conn)
        lock = locks.setdefault(room.code, asyncio.Lock())
        bucket = TokenBucket(settings.rate_burst, settings.rate_per_second)
        # serverTime: the phone counts down to the server's private-turn deadline on this clock (ADR 0013)
        await websocket.send_json({"type": "welcome", "role": role, "room": room.code, "serverTime": round(now() * MS)})
        await send_projection(room, conn, full=True)
        try:
            while True:
                text = await websocket.receive_text()
                if len(text.encode()) > settings.max_message_bytes:
                    await websocket.close(code=MESSAGE_TOO_BIG)
                    break
                if not bucket.take():
                    await websocket.send_json({"type": "rejected", "code": "rate_limited", "message": "too many messages"})
                    continue
                try:
                    intent = INTENT.validate_json(text)
                except ValidationError as e:
                    where = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
                    await websocket.send_json({"type": "invalid", "fields": where})
                    continue
                if role == DISPLAY:
                    await websocket.send_json({"type": "rejected", "code": "read_only", "message": "the display cannot act"})
                    continue
                async with lock:
                    before = len(room.game.events)
                    try:
                        room.game.submit(role, intent.intent, **intent.args())
                        registry.record(room, before)
                    except Rejection as r:
                        log.info("rejected room=%s role=%s intent=%s code=%s", room.code, role, intent.intent, r.code)
                        await websocket.send_json({"type": "rejected", "code": r.code, "message": str(r)})
                        continue
                    log.info("accepted room=%s role=%s intent=%s", room.code, role, intent.intent)
                    await broadcast(room, before)
        except WebSocketDisconnect:
            pass
        finally:
            if conn in connections.get(room.code, []):
                connections[room.code].remove(conn)

    return app
