# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R3, blueprint §6.2 `linking.code` (ADR 0016, proposed): an irrigation scheme's player may bring the personal linking
code made before the session. It is recorded in a `self` event that only that scheme's own projection carries; the
Authority (the facilitator) gives none. The code links survey answers without identity: it is never public."""

import json
from pathlib import Path

import pytest
from test_record import ROLES, SHEET, clock, nonce, setup

from fairflow_engine import AUTHORITY, Game, Rejection, audit, project
from fairflow_engine.record import LINKING_CODE_MAX

CODE = "AB03"  # test input: a participant-made code (blueprint §6.2 example: mother's initials + birth month)


def game(research: bool = False) -> Game:
    return Game.create(setup(), "c", "room", {"appVersion": "test"}, clock(), nonce(0), researchEnabled=research)


def join(g: Game, role: str, code: str | None, research: bool | None = None) -> None:
    g.submit(
        role,
        "join",
        deviceHash=f"h-{role}",
        participationAcknowledged=True,
        researchConsent=research,
        infoSheetVersion=SHEET,
        presurveyComplete=False,
        linkingCode=code,
    )


def test_a_scheme_s_code_is_recorded_for_its_own_eyes_only():
    g = game()
    join(g, ROLES[0], CODE)
    joined, linked = g.events[-2], g.events[-1]
    assert joined["type"] == "player.joined" and CODE not in str(joined["payload"])
    assert (linked["type"], linked["actor"], linked["visibility"], linked["payload"]) == (
        "linking.code",
        ROLES[0],
        "self",
        {"role": ROLES[0], "code": CODE},
    )
    for viewer in ["public", AUTHORITY, *ROLES[1:]]:
        assert all(e["type"] != "linking.code" for e in project(g.events, viewer)), viewer
    assert any(e["type"] == "linking.code" for e in project(g.events, ROLES[0]))
    assert audit(g.setup, g.events) == []


def test_a_code_is_optional_in_a_course_only_room_and_without_one_nothing_is_written():
    """The maintainer, 2026-10-15: required only when research is enabled."""
    g = game()
    join(g, ROLES[0], None)
    assert g.events[-1]["type"] == "player.joined"


@pytest.mark.parametrize(
    "role,code,expected",
    [
        (AUTHORITY, CODE, "no_linking_code"),  # the facilitator is not a survey participant
        (ROLES[0], "", "bad_linking_code"),
        (ROLES[0], "ab03", "bad_linking_code"),  # the phone sends it normalised: capitals and digits only
        (ROLES[0], "AB 03", "bad_linking_code"),
        (ROLES[0], "A" * (LINKING_CODE_MAX + 1), "bad_linking_code"),  # one character over the input bound
    ],
)
def test_what_a_code_may_be(role, code, expected):
    g = game()
    with pytest.raises(Rejection) as e:
        join(g, role, code)
    assert e.value.code == expected
    assert not g.events[1:]  # nothing was written: the join was refused whole


def test_a_join_that_sends_no_linking_code_field_still_works():
    g = game()
    g.submit(
        ROLES[0],
        "join",
        deviceHash="h",
        participationAcknowledged=True,
        researchConsent=None,
        infoSheetVersion=SHEET,
        presurveyComplete=False,
    )
    assert g.events[-1]["type"] == "player.joined"


def test_the_engine_and_the_phone_share_one_length_bound():
    content = Path(__file__).resolve().parents[3] / "content" / "linking-code.json"
    assert json.loads(content.read_text(encoding="utf-8"))["maxLength"] == LINKING_CODE_MAX


@pytest.mark.parametrize("answer", [True, False])
def test_while_research_is_enabled_a_scheme_needs_a_code_whatever_its_research_answer(answer):
    """The maintainer, 2026-10-15: required only when research is enabled. Read per room, so every scheme gives one,
    whatever its own research answer (an open question in ADR 0016)."""
    g = game(research=True)
    with pytest.raises(Rejection) as e:
        join(g, ROLES[0], None, research=answer)
    assert e.value.code == "linking_code_needed"
    join(g, ROLES[0], CODE, research=answer)
    assert g.events[-1]["type"] == "linking.code"


def test_the_authority_needs_no_code_while_research_is_enabled():
    g = game(research=True)
    join(g, AUTHORITY, None)
    assert g.events[-1]["type"] == "player.joined"
