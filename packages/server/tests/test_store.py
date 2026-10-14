# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0012: the room store. A restart resumes a game where it stood; a room is deleted, from memory and from the file,
a TTL after its last event; no token is written in plain; a record that does not check out is not served; a failed
write undoes the move."""

from __future__ import annotations

import json
import sqlite3
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from fairflow_engine import AUTHORITY, Rejection, audit
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from test_server import ORIGIN, connect, join_body, open_room

from fairflow_server.app import create_app
from fairflow_server.rooms import RoomRegistry
from fairflow_server.settings import Settings
from fairflow_server.store import Store

HOUR = 3600.0
MARKER = "feedface" * 8  # test input: a device hash to look for in the file's bytes


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0  # test input: any wall-clock start

    def __call__(self) -> float:
        return self.t


def settings(tmp_path: Path, **kw: Any) -> Settings:
    return Settings(allowed_origins=(ORIGIN,), store_path=tmp_path / "rooms.sqlite", **kw)


def rows(path: Path) -> dict[str, int]:
    db = sqlite3.connect(path)
    try:
        counts = {
            "rooms": "SELECT COUNT(*) FROM rooms",
            "tokens": "SELECT COUNT(*) FROM tokens",
            "events": "SELECT COUNT(*) FROM events",
        }
        return {t: db.execute(q).fetchone()[0] for t, q in counts.items()}
    finally:
        db.close()


def seated(reg: RoomRegistry) -> str:
    room, _, _ = reg.create("default-basin", "test")
    for role in room.free_roles():
        reg.join(room.code, role, MARKER if role == "A" else f"hash-{role}", True, None, reg.sheet_version, True)
    return room.code


def act(reg: RoomRegistry, code: str, who: str, intent: str, **args: Any) -> None:
    room = reg.get(code)
    before = len(room.game.events)
    room.game.submit(who, intent, **args)
    reg.record(room, before)


def one_season(reg: RoomRegistry, code: str) -> None:
    act(reg, code, AUTHORITY, "start_season")
    act(reg, code, AUTHORITY, "propose", lens="proportional")
    roles = [s.id for s in reg.get(code).game.setup.schemes]
    for r in roles:
        act(reg, code, r, "vote", lens="proportional")
    act(reg, code, AUTHORITY, "close_vote")
    for r in roles:
        act(reg, code, r, "commit", pumps=0.0)


def test_a_restart_resumes_a_game_mid_season(tmp_path: Path) -> None:
    s = settings(tmp_path)
    with TestClient(create_app(s)) as first:
        info = open_room(first)
        roles = [r for r in info if r not in ("room", "authority", "display")]
        with ExitStack() as stack:
            sockets = {who: connect(first, stack, info["room"], info[who]) for who in ["authority", *roles]}

            def send(who: str, message: dict[str, Any]) -> None:
                sockets[who].send_text(json.dumps(message))
                for ws in sockets.values():
                    assert ws.receive_json()["type"] in ("events", "sync")

            send("authority", {"intent": "start_season"})
            send("authority", {"intent": "propose", "lens": "proportional"})
            for r in roles:
                send(r, {"intent": "vote", "lens": "proportional"})
            send("authority", {"intent": "close_vote"})
            send(roles[0], {"intent": "commit", "pumps": 1.0})  # one scheme has committed when the server stops
        before = list(first.app.state.registry.rooms[info["room"]].game.events)  # type: ignore[attr-defined]

    with TestClient(create_app(s)) as second:
        room = second.app.state.registry.get(info["room"])  # type: ignore[attr-defined]
        assert room.game.events == before and room.game.state.phase == "private"
        assert second.get(f"/rooms/{info['room']}").json()["freeRoles"] == []
        with ExitStack() as stack:
            again = {r: connect(second, stack, info["room"], info[r]) for r in roles[1:]}  # the stored tokens still work
            for r in roles[1:]:
                again[r].send_text(json.dumps({"intent": "commit", "pumps": 0.0}))
                for ws in again.values():
                    assert ws.receive_json()["type"] == "events"
        assert any(e["type"] == "season.resolved" for e in room.game.events)
        assert not [p for p in audit(room.game.setup, room.game.events) if not p.startswith("note:")]


def test_a_room_is_deleted_a_ttl_after_its_last_event(tmp_path: Path) -> None:
    clock, s = Clock(), settings(tmp_path)
    reg = RoomRegistry(s, clock)
    code = seated(reg)
    clock.t += 23 * HOUR
    act(reg, code, AUTHORITY, "start_season")  # a move restarts the 24 hours
    clock.t += 23 * HOUR
    assert reg.get(code).code == code
    assert reg.sweep() == []
    clock.t += 2 * HOUR
    with pytest.raises(Rejection) as gone:
        reg.get(code)
    assert gone.value.code == "unknown_room"
    assert rows(s.store_path) == {"rooms": 0, "tokens": 0, "events": 0}  # type: ignore[arg-type]
    reg.store.close()  # type: ignore[union-attr]
    assert MARKER.encode() not in s.store_path.read_bytes()  # type: ignore[union-attr]  # overwritten, not just unlinked


def test_the_sweep_deletes_idle_rooms_and_closes_their_connections(tmp_path: Path) -> None:
    clock, s = Clock(), settings(tmp_path)
    app = create_app(s, clock)
    with TestClient(app) as client:
        info = open_room(client)
        with ExitStack() as stack:
            ws = connect(client, stack, info["room"], info["authority"])
            clock.t += 25 * HOUR
            client.portal.call(app.state.sweep)  # type: ignore[union-attr]
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1008  # the client then shows the room as gone and stops retrying
        assert client.get(f"/rooms/{info['room']}").status_code == 404
    assert rows(s.store_path) == {"rooms": 0, "tokens": 0, "events": 0}  # type: ignore[arg-type]


def test_no_token_is_written_in_plain(tmp_path: Path) -> None:
    s = settings(tmp_path)
    with TestClient(create_app(s)) as client:
        info = open_room(client)
    data = s.store_path.read_bytes()  # type: ignore[union-attr]
    for who in ("authority", "display", "A", "B", "C"):
        assert info[who].encode() not in data, who
    assert rows(s.store_path)["tokens"] == 5  # type: ignore[arg-type]


@pytest.mark.parametrize("tamper", ["season", "nonce", "gap"])
def test_a_store_that_does_not_check_out_is_not_served(tmp_path: Path, tamper: str) -> None:
    clock, s = Clock(), settings(tmp_path)
    reg = RoomRegistry(s, clock)
    code = seated(reg)
    one_season(reg, code)
    reg.store.close()  # type: ignore[union-attr]
    db = sqlite3.connect(s.store_path)  # type: ignore[arg-type]
    if tamper == "season":  # a resolved season edited on disk
        seq, text = db.execute("SELECT seq, event FROM events WHERE event LIKE '%season.resolved%'").fetchone()
        e = json.loads(text)
        e["payload"]["sealed"]["pumpsBy"]["A"] = 3.0
        e["payload"]["sealed"]["P"][0] = 3.0
        db.execute("UPDATE events SET event = ? WHERE code = ? AND seq = ?", (json.dumps(e), code, seq))
    elif tamper == "nonce":  # a nonce that does not match the commitments
        db.execute("UPDATE rooms SET nonce = ? WHERE code = ?", ("0" * 32, code))
    else:  # an event missing from the record
        db.execute("DELETE FROM events WHERE code = ? AND seq = 3", (code,))
    db.commit()
    db.close()
    again = RoomRegistry(s, clock)
    with pytest.raises(Rejection):
        again.get(code)
    clock.t += 25 * HOUR
    assert again.sweep() == [code]  # set aside, then deleted with the rest
    assert rows(s.store_path)["rooms"] == 0  # type: ignore[arg-type]


def test_a_failed_write_undoes_the_move(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    s = settings(tmp_path)
    app = create_app(s)
    with TestClient(app) as client:
        code = client.post("/rooms", json={"scenario": "default-basin"}).json()["room"]
        room = app.state.registry.get(code)
        events = len(room.game.events)

        def fail(*_: Any) -> None:
            raise sqlite3.OperationalError("disk I/O error")  # test input: a full or failing disk

        monkeypatch.setattr(app.state.registry.store, "append", fail)
        r = client.post(f"/rooms/{code}/join", json=join_body("A", "hash-A-fail"))
        assert r.status_code == 503 and r.json()["detail"]["code"] == "storage_failed"
        assert len(room.game.events) == events and "A" in room.free_roles()


def test_store_and_ttl_settings_and_what_the_server_refuses(tmp_path: Path) -> None:
    env = Settings.from_env({"FAIRFLOW_STORE": str(tmp_path / "x.sqlite"), "FAIRFLOW_ROOM_TTL_HOURS": "48"})
    assert env.store_path == tmp_path / "x.sqlite" and env.room_ttl_hours == 48.0
    assert Settings.from_env({}).store_path is None and Settings.from_env({}).room_ttl_hours == 24.0
    with pytest.raises(RuntimeError, match="information sheet"):  # the sheet says 24 hours
        RoomRegistry(settings(tmp_path, room_ttl_hours=48.0))
    with pytest.raises(RuntimeError, match="research mode"):  # nothing would be left to analyse
        RoomRegistry(settings(tmp_path, research_enabled=True))


def test_a_websocket_move_that_cannot_be_written_is_told_to_no_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR 0012: a move is on disk before anyone hears of it. If the write fails, the actor is told so and no other
    screen hears of the move; the next move that is written is the first news anyone gets."""
    s = settings(tmp_path)
    app = create_app(s)
    with TestClient(app) as client:
        info = open_room(client)
        room = app.state.registry.get(info["room"])
        with ExitStack() as stack:
            authority = connect(client, stack, info["room"], info["authority"])
            display = connect(client, stack, info["room"], info["display"])
            before = list(room.game.events)

            def fail(*_: Any) -> None:
                raise sqlite3.OperationalError("disk I/O error")  # test input: a full or failing disk

            with monkeypatch.context() as m:
                m.setattr(app.state.registry.store, "append", fail)
                authority.send_text(json.dumps({"intent": "start_season"}))
                assert authority.receive_json()["code"] == "storage_failed"
            assert room.game.events == before
            authority.send_text(json.dumps({"intent": "start_season"}))  # written this time
            first = display.receive_json()  # the display's first message since its sync: the written move
            assert first["type"] == "events" and first["events"][0]["seq"] == len(before) + 1


def test_a_store_written_on_a_failed_transaction_keeps_none_of_it(tmp_path: Path) -> None:
    """Store.append writes one intent's events and token hashes in one transaction: if any row fails, none is kept."""
    store = Store(tmp_path / "rooms.sqlite")
    store.create("ROOM1", {}, "nonce", 1.0)  # test input: a room code, an empty scenario, a nonce and a time
    store.append("ROOM1", [{"seq": 1, "type": "game.created"}], 2.0, [("hash-1", "A")])
    with pytest.raises(sqlite3.IntegrityError):  # the second token row repeats a hash already stored
        store.append("ROOM1", [{"seq": 2, "type": "player.joined"}], 3.0, [("hash-1", "B")])
    (stored,) = store.rooms()
    assert [e["seq"] for e in stored.events] == [1] and stored.last_event == 2.0 and stored.tokens == {"hash-1": "A"}
    store.append("ROOM1", [{"seq": 2, "type": "player.joined"}], 3.0, [("hash-2", "B")])  # the store still takes writes
    store.close()
