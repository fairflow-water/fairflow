# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0011: part 1 (taking part) is required; an irrigation scheme's research answer is required while research is
enabled and refused otherwise; it goes to a `server` event that no projection returns, before or after the debrief."""

import pytest
from test_actions_goals import season
from test_record import ROLES, SHEET, clock, nonce, setup

from fairflow_engine import AUTHORITY, Game, Rejection, audit, project, replay

VIEWERS = ["public", AUTHORITY, *ROLES]


def game(research: bool) -> Game:
    return Game.create(setup(), "c", "room", {"appVersion": "test"}, clock(), nonce(0), researchEnabled=research)


def join(g: Game, role: str, answer: bool | None, acknowledged: bool = True) -> None:
    g.submit(
        role,
        "join",
        deviceHash=f"h-{role}",
        participationAcknowledged=acknowledged,
        researchConsent=answer,
        infoSheetVersion=SHEET,
        presurveyComplete=False,
    )


def test_part_one_is_required():
    g = game(research=False)
    with pytest.raises(Rejection) as e:
        join(g, ROLES[0], None, acknowledged=False)
    assert e.value.code == "not_acknowledged"


def test_course_only_takes_no_research_answer():
    g = game(research=False)
    with pytest.raises(Rejection) as e:
        join(g, ROLES[0], True)
    assert e.value.code == "research_not_asked"
    join(g, ROLES[0], None)
    assert not any(e["type"] == "research.consent" for e in g.events)


def test_research_mode_needs_a_yes_or_no_from_every_farm_but_not_the_facilitator():
    g = game(research=True)
    with pytest.raises(Rejection) as e:
        join(g, ROLES[0], None)
    assert e.value.code == "research_answer_needed"
    with pytest.raises(Rejection) as e:
        join(g, AUTHORITY, False)
    assert e.value.code == "research_not_asked"
    join(g, AUTHORITY, None)
    assert [e["type"] for e in g.events].count("research.consent") == 0


def test_the_research_answer_reaches_no_viewer_before_or_after_the_debrief():
    g = game(research=True)
    answers = dict(zip(ROLES, [True, False, True], strict=True))
    for role in ROLES:
        join(g, role, answers[role])
    join(g, AUTHORITY, None)
    stored = {e["payload"]["role"]: e["payload"]["researchConsent"] for e in g.events if e["type"] == "research.consent"}
    assert stored == answers and all(e["visibility"] == "server" for e in g.events if e["type"] == "research.consent")
    while replay(g.events).phase != "ended":
        season(g)
    g.submit(AUTHORITY, "open_debrief", perPlayer=True)
    for viewer in VIEWERS:
        seen = project(g.events, viewer)
        assert not any("researchConsent" in str(e["payload"]) for e in seen)
        joined = [e["payload"] for e in seen if e["type"] == "player.joined"]
        assert all(
            set(p) == {"role", "deviceId", "participationAcknowledged", "infoSheetVersion", "presurveyComplete"}
            for p in joined
        )
    assert audit(g.setup, g.events) == []
