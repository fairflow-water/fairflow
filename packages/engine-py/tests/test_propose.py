# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""R7: "Lenses are proposed aloud; the Authority taps them." Only the Authority sends `propose` (issue #34, accepted
by the maintainer 2026-10-15); the engine refuses it from any other role and records nothing. The server's side is
in packages/server/tests/test_propose_wire.py."""

import pytest
from test_record import ROLES, new_game

from fairflow_engine import AUTHORITY, ENGINE, Rejection


@pytest.mark.parametrize("actor", [*ROLES, ENGINE])
def test_only_the_authority_proposes(actor):
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    before = len(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(actor, "propose", lens="proportional")
    assert e.value.code == "not_authority"
    assert len(g.events) == before


def test_the_authority_proposes_and_is_recorded_as_proposer():
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="proportional")
    e = g.events[-1]
    assert (e["type"], e["actor"]) == ("lens.proposed", AUTHORITY)
    assert e["payload"] == {"lens": "proportional", "proposer": AUTHORITY}


def test_a_scheme_cannot_propose_in_the_practice_round_either():
    g = new_game()
    g.submit(AUTHORITY, "start_tutorial")
    before = len(g.events)
    with pytest.raises(Rejection) as e:
        g.submit(ROLES[0], "propose", lens="proportional")
    assert e.value.code == "not_authority"
    assert len(g.events) == before
