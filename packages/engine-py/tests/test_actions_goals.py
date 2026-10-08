# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Module 1 actions, the private turn, band words, private goals and the debrief brief. Expected values are read from the
blueprint's §3.3 dynamic fixtures."""

import blueprint as bp
import pytest
from test_record import ROLES, kelvara_game, new_game

from fairflow_engine import AUTHORITY, Rejection, audit, project, replay

S33 = bp.section("### 3.3 Dynamic fixtures")


def season(g, lens="proportional", pumps=None, actions=None):
    """One season: the Authority proposes `lens`, every farm votes for it, then each commits."""
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens=lens)
    for r in ROLES:
        g.submit(r, "vote", lens=lens)
    g.submit(AUTHORITY, "close_vote")
    for r in ROLES:
        g.submit(r, "commit", pumps=(pumps or {}).get(r, 0.0), action=(actions or {}).get(r))


def climate(g, n):
    """The season's climate, with its schemes indexed by id for the tests."""
    c = dict(next(e for e in g.events if e["type"] == "season.climate" and e["season"] == n)["payload"])
    c["schemes"] = {v["id"]: v for v in c["schemes"]}
    return c


def resolved(g, n):
    return next(e for e in g.events if e["type"] == "season.resolved" and e["season"] == n)["payload"]["sealed"]


def test_orchard_lag():
    """§3.3 'B plays Orchard in season 2 | D_B, K_B, p_B from season 3; L_B −= 10 in season 2' (ADR 0007: the basin's
    orchard crop at B's own area and method, the diversion recomputed for B's β)."""
    demand, capacity, price, cost = bp.grab(
        r"D\\_B = NUM, K\\_B = NUM, p\\_B = NUM from season 3; L\\_B −= NUM in season 2", S33
    )
    g = kelvara_game(gameLength=(5, 5))
    season(g)
    season(g, actions={"B": "orchard"})
    season(g)
    assert climate(g, 2)["schemes"]["B"]["demandMm3"] != demand  # not yet in force in season 2
    for key, want in (("demandMm3", demand), ("capacityT", capacity), ("price", price)):
        assert climate(g, 3)["schemes"]["B"][key] == pytest.approx(float(want), abs=want.tol)
    b = resolved(g, 2)["roles"].index("B")
    assert resolved(g, 2)["actionCost"][b] == pytest.approx(float(cost), abs=cost.tol)
    assert audit(g.setup, g.events) == []


def test_drip_then_expand_is_the_rebound():
    """§3.3 'C: Drip season 1, Expand season 2 | D_C, K_C from season 2; D_C, K_C, area from season 3; ΣD … then …'
    (ADR 0007: Drip keeps 95 % of the consumption and recomputes the diversion at β = 0.90)."""
    d2, k2, d3, k3, area3, sum2, sum3 = bp.grab(
        r"D\\_C = NUM, K\\_C = NUM from season 2; D\\_C = NUM, K\\_C = NUM, area NUM ha from season 3; ΣD NUM then NUM", S33
    )
    g = kelvara_game(gameLength=(5, 5))
    season(g, actions={"C": "drip"})
    season(g, actions={"C": "expand"})
    season(g)
    s2, s3 = climate(g, 2)["schemes"], climate(g, 3)["schemes"]
    for got, want in (
        (s2["C"]["demandMm3"], d2),
        (s2["C"]["capacityT"], k2),
        (s3["C"]["demandMm3"], d3),
        (s3["C"]["capacityT"], k3),
        (s3["C"]["areaHa"], area3),
    ):
        assert got == pytest.approx(float(want), abs=want.tol)
    assert sum(v["demandMm3"] for v in s2.values()) == pytest.approx(float(sum2), abs=sum2.tol)
    assert sum(v["demandMm3"] for v in s3.values()) == pytest.approx(float(sum3), abs=sum3.tol)
    assert audit(g.setup, g.events) == []


def test_actions_follow_each_schemes_method():
    """ADR 0007: the citrus estate on drip may only Expand; the paddy may not play Drip."""
    g = kelvara_game(gameLength=(5, 5))
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "close_vote")
    for role, action in (("A", "orchard"), ("A", "drip"), ("B", "drip")):
        with pytest.raises(Rejection) as e:
            g.submit(role, "commit", pumps=0.0, action=action)
        assert e.value.code == "action_not_for_this_scheme"


def test_orchard_and_drip_once_expand_repeatable():
    """§4.3: Orchard 'once', Drip 'once', Expand 'repeatable'; a refused commit leaves the record unchanged."""
    g = kelvara_game(gameLength=(5, 5))
    season(g, actions={"B": "orchard", "C": "expand"})
    season(g, actions={"C": "expand"})
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "close_vote")
    before = list(g.events)
    with pytest.raises(Rejection):
        g.submit("B", "commit", pumps=0.0, action="orchard")
    with pytest.raises(Rejection):
        g.submit("B", "commit", pumps=0.0, action="steal")
    assert g.events == before


def test_goal_attainability_full_cooperation():
    """§3.3 goal attainability: under proportional with the full deck A reaches the printed share of its potential and
    meets its R15 goal; the engine's 'full-demand potential' is Σ pK/100 (§2.4)."""
    share, goal = bp.grab(r"under proportional with the full deck A reaches NUM % of potential \(R15 goal NUM %\)", S33)
    deck_size = sum(int(v) for v in bp.grab(r"deck NUM W / NUM N / NUM D", bp.section("### 2.2 Parameters and grounding")))
    g = kelvara_game(gameLength=(deck_size, deck_size))
    while replay(g.events).phase != "ended":
        season(g)
    a = next(e["payload"] for e in g.events if e["type"] == "goal.result" and e["payload"]["role"] == "A")
    assert a["value"] * 100 == pytest.approx(float(share), abs=share.tol)
    assert a["threshold"] * 100 == pytest.approx(float(goal), abs=goal.tol) and a["met"]
    ended = next(e for e in g.events if e["type"] == "game.ended")["payload"]
    assert ended["authorityGoal"]["met"] and ended["authorityGoal"]["meanPumping"] == 0


def test_private_turn_previews_go_only_to_their_farm():
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "close_vote")
    opened = [e for e in g.events if e["type"] == "private.opened"]
    assert sorted(e["payload"]["role"] for e in opened) == sorted(ROLES)
    for viewer in ["public", AUTHORITY, *ROLES]:
        seen = [e["payload"]["role"] for e in project(g.events, viewer) if e["type"] == "private.opened"]
        assert seen == ([viewer] if viewer in ROLES else [])
    a = next(e["payload"] for e in opened if e["payload"]["role"] == "A")
    assert [o["pumps"] for o in a["options"]] == list(range(int(g.setup.basin.pump.cap) + 1))
    assert set(a["options"][0]["points"]) == {"none", *g.setup.actions}
    for o in a["options"]:
        for action, cost in a["actions"].items():
            assert o["points"][action] == pytest.approx(o["points"]["none"] - cost, abs=1e-6)


def test_band_words_and_brief_are_public():
    g = new_game()
    while replay(g.events).phase != "ended":
        season(g, pumps={"A": g.setup.basin.pump.cap})
    pub = [e for e in project(g.events, "public") if e["type"] == "season.resolved"]
    assert all(set(e["payload"]["public"]["bands"]) == {"ePJ", "eSE", "F"} for e in pub)
    assert all("adequacyBands" in e["payload"] for e in project(g.events, "public") if e["type"] == "allocation.issued")
    brief = next(e for e in project(g.events, "public") if e["type"] == "game.ended")["payload"]["brief"]
    assert brief["heaviestPumping"]["pumpsTotal"] == max(e["payload"]["public"]["pumpsTotal"] for e in pub)
    assert brief["lensChanges"] == 0
    assert not any(e["type"] == "goal.result" for e in project(g.events, "public"))
    assert audit(g.setup, g.events) == []
