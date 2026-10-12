# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0013: the server times the private turn. On a test clock: a phone that is gone is committed for at the server's
deadline, a phone that commits in time is never overridden, no client can send the server's intent, and the welcome
gives the phone the server's time."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_server import ORIGIN, connect, open_room

from fairflow_server.app import MS, TIMER_TICK_S, create_app
from fairflow_server.rooms import load_registry
from fairflow_server.settings import REPO, Settings

SETTINGS = Settings(allowed_origins=(ORIGIN,))
SESSION = json.loads((REPO / "packages" / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))["session"]
DECISION_S = SESSION["decisionS"]
GRACE_S = SESSION.get("privateTurnGraceS", load_registry(SETTINGS)["session.privateTurnGraceS"])
WAIT_S = 10 * TIMER_TICK_S  # test input: how long the test waits for a timer that should fire within one tick


class Clock:
    """Wall time plus an offset the test moves forward."""

    def __init__(self) -> None:
        self.offset = 0.0

    def __call__(self) -> float:
        return time.time() + self.offset


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock: Clock) -> Iterator[TestClient]:
    with TestClient(create_app(SETTINGS, now=clock)) as c:
        yield c


def record(client: TestClient, room: str) -> list[dict[str, Any]]:
    return list(client.app.state.registry.get(room).game.events)  # type: ignore[attr-defined]


def phase(client: TestClient, room: str) -> str:
    return str(client.get(f"/rooms/{room}").json()["phase"])


def wait_for_phase(client: TestClient, room: str, wanted: tuple[str, ...]) -> str:
    end = time.monotonic() + WAIT_S
    while (now := phase(client, room)) not in wanted and time.monotonic() < end:
        time.sleep(TIMER_TICK_S / 10)  # test input: polling interval
    return now


def act(sockets: dict[str, Any], who: str, message: dict[str, Any]) -> None:
    sockets[who].send_text(json.dumps(message))
    for name, ws in sockets.items():
        assert ws.receive_json()["type"] == "events", name


def open_private_turn(sockets: dict[str, Any], roles: list[str], start: str = "start_season") -> None:
    act(sockets, "authority", {"intent": start})
    act(sockets, "authority", {"intent": "propose", "lens": "proportional"})
    for r in roles:
        act(sockets, r, {"intent": "vote", "lens": "proportional"})
    act(sockets, "authority", {"intent": "close_vote"})


def commit(sockets: dict[str, Any], who: str, **extra: Any) -> None:
    act(sockets, who, {"intent": "commit", "pumps": 0.0, **extra})


def roles_of(info: dict[str, str]) -> list[str]:
    return [r for r in info if r not in ("room", "authority", "display")]


@pytest.mark.parametrize("start", ["start_season", "start_tutorial"])
def test_a_phone_that_is_gone_is_committed_for_at_the_deadline(client: TestClient, clock: Clock, start: str) -> None:
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]}
        open_private_turn(sockets, roles, start)
        sockets.pop(roles[-1]).close()  # the last scheme's phone is gone before its private turn
        for r in roles[:-1]:
            commit(sockets, r)
        clock.offset = DECISION_S - 1  # test input: just before the phone's deadline nothing happens
        time.sleep(2 * TIMER_TICK_S)  # test input: two ticks of the timer
        assert phase(client, info["room"]) == "private"
        clock.offset = DECISION_S + GRACE_S
        assert wait_for_phase(client, info["room"], ("reveal", "ended")) in ("reveal", "ended")
        for who, ws in sockets.items():
            msg = ws.receive_json()
            assert msg["type"] == "events", who
            assert "timeoutBy" not in json.dumps(msg), who
            assert not any("byTimeout" in e["payload"] for e in msg["events"] if e["type"] == "action.played"), who
    plays = [e["payload"] for e in record(client, info["room"]) if e["type"] == "action.played"]
    assert [p.get("timeoutBy") for p in plays] == [None] * (len(roles) - 1) + ["server"]
    assert plays[-1]["pumps"] == 0 and plays[-1]["action"] is None


def test_a_phone_that_commits_in_time_is_never_overridden(client: TestClient, clock: Clock) -> None:
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]}
        open_private_turn(sockets, roles)
        commit(sockets, roles[0], byTimeout=True)  # its own timer ran out
        for r in roles[1:]:
            commit(sockets, r)
        assert phase(client, info["room"]) in ("reveal", "ended")
        clock.offset = DECISION_S + GRACE_S + WAIT_S
        time.sleep(2 * TIMER_TICK_S)  # test input: the season's timer wakes and must do nothing
    plays = [e["payload"] for e in record(client, info["room"]) if e["type"] == "action.played"]
    assert [p.get("timeoutBy") for p in plays] == ["phone"] + [None] * (len(roles) - 1)


def test_the_next_season_gets_its_own_timer(client: TestClient, clock: Clock) -> None:
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]}
        open_private_turn(sockets, roles)
        for r in roles:
            commit(sockets, r)
        assert phase(client, info["room"]) == "reveal"  # the scenario's games last more than one season
        open_private_turn(sockets, roles)
        time.sleep(2 * TIMER_TICK_S)  # test input: the first season's timer is still asleep and must not act
        assert phase(client, info["room"]) == "private"
        clock.offset = DECISION_S + GRACE_S + TIMER_TICK_S
        assert wait_for_phase(client, info["room"], ("reveal", "ended")) in ("reveal", "ended")
    plays = [e for e in record(client, info["room"]) if e["type"] == "action.played"]
    assert {e["season"] for e in plays if e["payload"].get("timeoutBy") == "server"} == {2}


def test_no_client_can_send_the_server_intent(client: TestClient) -> None:
    info = open_room(client)
    roles = roles_of(info)
    with ExitStack() as stack:
        sockets = {w: connect(client, stack, info["room"], info[w]) for w in ["authority", "display", *roles]}
        open_private_turn(sockets, roles)
        season = record(client, info["room"])[-1]["season"]
        for who in ["authority", "display", roles[0]]:
            sockets[who].send_text(json.dumps({"intent": "timeout_private", "season": season}))
            assert sockets[who].receive_json()["type"] == "invalid", who
        sockets[roles[0]].send_text(json.dumps({"intent": "commit", "pumps": 0.0, "byTimeout": False}))
        assert sockets[roles[0]].receive_json() == {"type": "invalid", "fields": ["commit.byTimeout"]}
    assert phase(client, info["room"]) == "private"
    assert not any(e["type"] == "action.played" for e in record(client, info["room"]))


def test_the_welcome_gives_the_server_time(client: TestClient, clock: Clock) -> None:
    info = open_room(client)
    clock.offset = DECISION_S  # test input: a server clock ahead of the phone's
    with client.websocket_connect(f"/rooms/{info['room']}/ws", headers={"origin": ORIGIN}) as ws:
        sent = time.time()
        ws.send_text(json.dumps({"token": info["authority"]}))
        welcome = ws.receive_json()
    assert welcome["type"] == "welcome"
    assert abs(welcome["serverTime"] / MS - (sent + DECISION_S)) < TIMER_TICK_S  # tolerance: the test's own run time
