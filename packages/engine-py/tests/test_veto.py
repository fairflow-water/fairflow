# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R8 (ADR 0015): the Authority holds one veto per game, after which the remaining lenses are re-voted."""

import pytest
from test_record import ROLES, new_game, play_season
from test_tutorial import tutorial

from fairflow_engine import AUTHORITY, Rejection, audit, project, replay


def open_vote(g, lenses=("proportional", "egalitarian", "capability")):
    g.submit(AUTHORITY, "start_season")
    for lens in lenses:
        g.submit(AUTHORITY, "propose", lens=lens)
    return g


def chosen(g):
    return [e for e in g.events if e["type"] == "lens.chosen"][-1]["payload"]


def refused(g, actor, intent, **kw):
    with pytest.raises(Rejection) as e:
        g.submit(actor, intent, **kw)
    return e.value.code


def test_a_veto_removes_the_lens_clears_the_votes_and_the_rest_is_re_voted():
    g = open_vote(new_game())
    for role in ROLES:
        g.submit(role, "vote", lens="proportional")
    g.submit(AUTHORITY, "veto", lens="proportional")
    s = replay(g.events)
    assert s.phase == "vote" and s.proposals == ["egalitarian", "capability"] and s.votes == {}
    vetoed = g.events[-1]
    assert (vetoed["type"], vetoed["actor"], vetoed["visibility"], vetoed["payload"]) == (
        "lens.vetoed",
        AUTHORITY,
        "public",
        {"lens": "proportional"},
    )
    assert refused(g, "A", "vote", lens="proportional") == "not_proposed"
    assert refused(g, AUTHORITY, "propose", lens="proportional") == "vetoed"
    for role in ROLES:
        g.submit(role, "vote", lens="egalitarian")
    g.submit(AUTHORITY, "close_vote")
    p = chosen(g)
    assert (p["lens"], p["veto"], p["revote"]) == ("egalitarian", "proportional", True)
    assert p["tally"] == {"egalitarian": len(ROLES)}  # the cleared votes count for nothing
    assert replay(g.events).phase == "private"


def test_after_a_veto_no_new_lens_is_proposed_until_the_next_season():
    """R8: "the remaining lenses are re-voted" (ADR 0015, accepted): a lens nobody proposed does not join the re-vote."""
    g = open_vote(new_game())
    g.submit(AUTHORITY, "veto", lens="proportional")
    assert refused(g, AUTHORITY, "propose", lens="utilitarian") == "revote_only"
    for role in ROLES:
        g.submit(role, "vote", lens="egalitarian")
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="utilitarian")  # a new season: proposals are open again
    assert "utilitarian" in replay(g.events).proposals


def test_a_re_vote_can_tie_and_the_authority_breaks_it():
    g = open_vote(new_game())
    g.submit(AUTHORITY, "veto", lens="proportional")
    g.submit("A", "vote", lens="egalitarian")
    g.submit("B", "vote", lens="capability")
    g.submit(AUTHORITY, "close_vote")
    assert replay(g.events).phase == "tiebreak"
    g.submit(AUTHORITY, "break_tie", lens="capability")
    p = chosen(g)
    assert (p["lens"], p["tieBreak"], p["veto"], p["revote"]) == ("capability", True, "proportional", True)


def test_one_veto_per_game():
    g = open_vote(new_game())
    g.submit(AUTHORITY, "veto", lens="capability")
    assert refused(g, AUTHORITY, "veto", lens="egalitarian") == "veto_used"  # not twice in a season
    for role in ROLES:
        g.submit(role, "vote", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    open_vote(g)
    assert refused(g, AUTHORITY, "veto", lens="egalitarian") == "veto_used"  # nor in a later season


def test_a_season_without_a_veto_records_neither_field():
    g = new_game()
    play_season(g)
    assert "veto" not in chosen(g) and "revote" not in chosen(g)
    g = open_vote(new_game())
    g.submit(AUTHORITY, "veto", lens="capability")
    for role in ROLES:
        g.submit(role, "vote", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    play_season(g)  # the next season: the veto belonged to the last one
    assert "veto" not in chosen(g) and "revote" not in chosen(g)


@pytest.mark.parametrize(
    "actor,setup,lens,code",
    [
        ("A", "vote", "proportional", "not_authority"),  # only the Authority holds the veto
        (AUTHORITY, "vote", "talmud", "not_proposed"),  # a lens nobody proposed
        (AUTHORITY, "single", "proportional", "nothing_left"),  # nothing would be left to re-vote on
        (AUTHORITY, "closed", "egalitarian", "wrong_phase"),  # the vote is over
        (AUTHORITY, "tutorial", "utilitarian", "veto_not_in_tutorial"),  # the practice round is not scored
        (AUTHORITY, "tiebreak", "proportional", "wrong_phase"),  # a tie is the Authority's to break, not to veto
    ],
)
def test_what_a_veto_needs(actor, setup, lens, code):
    if setup == "tutorial":
        g = new_game()
        g.submit(AUTHORITY, "start_tutorial")
        for x in ("proportional", "utilitarian"):
            g.submit(AUTHORITY, "propose", lens=x)
    elif setup == "single":
        g = open_vote(new_game(), lenses=("proportional",))
    else:
        g = open_vote(new_game())
        if setup == "closed":
            for role in ROLES:
                g.submit(role, "vote", lens="proportional")
            g.submit(AUTHORITY, "close_vote")
        elif setup == "tiebreak":  # one vote on each proposal: a tie
            for role, x in zip(ROLES, ("proportional", "egalitarian", "capability"), strict=True):
                g.submit(role, "vote", lens=x)
            g.submit(AUTHORITY, "close_vote")
            assert replay(g.events).phase == "tiebreak"
    before = list(g.events)
    assert refused(g, actor, "veto", lens=lens) == code
    assert g.events == before


def test_the_practice_round_does_not_spend_the_veto():
    g = tutorial(new_game())
    open_vote(g)
    g.submit(AUTHORITY, "veto", lens="egalitarian")
    assert replay(g.events).vetoUsed


def test_every_screen_sees_the_veto_and_the_record_audits():
    g = open_vote(new_game())
    g.submit(AUTHORITY, "veto", lens="proportional")
    for viewer in [*ROLES, AUTHORITY, "public"]:
        assert any(e["type"] == "lens.vetoed" for e in project(g.events, viewer)), viewer
    for role in ROLES:
        g.submit(role, "vote", lens="capability")
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=0.0)
    assert audit(g.setup, g.events) == []
    assert replay(g.events).vetoUsed
