# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0018 decision 2 and issue #9: a role moves to another phone through a one-time link on the host page. The room
server, never a player, records the move: `authority.handover` for the Authority, `seat.transferred` for an irrigation
scheme, each with the season and the two devices' salted hashes. The role, the game and every result stay as they were."""

import pytest
from test_record import ROLES, new_game, play_season

from fairflow_engine import AUTHORITY, ENGINE, Rejection, audit, project, replay


def moves(g, kind):
    return [e for e in g.events if e["type"] == kind]


def test_only_the_room_server_moves_a_role():
    g = new_game()
    for actor in [*ROLES, AUTHORITY]:
        with pytest.raises(Rejection) as e:
            g.submit(actor, "transfer", role=ROLES[0], deviceHash="h-new")
        assert e.value.code == "not_engine"


def test_a_scheme_moves_to_another_phone_and_its_season_and_devices_are_recorded():
    g = new_game()
    play_season(g)
    g.submit(ENGINE, "transfer", role=ROLES[0], deviceHash="h-new")
    [e] = moves(g, "seat.transferred")
    assert (e["actor"], e["visibility"], e["season"]) == (ENGINE, "public", 1)
    assert e["payload"] == {"role": ROLES[0], "season": 1, "fromDevice": f"h-{ROLES[0]}", "toDevice": "h-new"}
    assert replay(g.events).players[ROLES[0]]["deviceId"] == "h-new"
    assert all(any(x["type"] == "seat.transferred" for x in project(g.events, v)) for v in ["public", *ROLES, AUTHORITY])
    assert audit(g.setup, g.events) == []


def test_a_second_move_starts_from_the_phone_of_the_first():
    g = new_game()
    g.submit(ENGINE, "transfer", role=ROLES[1], deviceHash="h-second")
    g.submit(ENGINE, "transfer", role=ROLES[1], deviceHash="h-third")
    first, second = moves(g, "seat.transferred")
    assert (first["payload"]["toDevice"], second["payload"]["fromDevice"]) == ("h-second", "h-second")


def test_the_authority_hand_over_is_its_own_event_and_the_role_stays_the_authority():
    g = new_game()
    play_season(g)
    play_season(g)
    g.submit(ENGINE, "transfer", role=AUTHORITY, deviceHash="h-student")
    [e] = moves(g, "authority.handover")
    assert e["payload"] == {"season": 2, "fromDevice": f"h-{AUTHORITY}", "toDevice": "h-student"}
    assert moves(g, "seat.transferred") == []
    assert AUTHORITY in replay(g.events).players
    play_season(g)  # the Authority's intents still work after the move: the role, not the device, is the actor
    assert audit(g.setup, g.events) == []


@pytest.mark.parametrize(
    ("role", "device", "code"),
    [
        ("Z", "h-new", "not_seated"),  # no such role at the table
        (ROLES[0], f"h-{ROLES[0]}", "same_device"),  # the phone already holds the role
        (ROLES[0], "", "bad_input"),  # every device has a hash
    ],
)
def test_what_a_move_needs(role, device, code):
    g = new_game()
    before = list(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(ENGINE, "transfer", role=role, deviceHash=device)
    assert e.value.code == code
    assert g.events == before
