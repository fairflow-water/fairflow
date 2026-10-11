# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Review E11: the private preview gives harvest and points only for pump levels the observed tank level guarantees,
and there it depends on public information alone, so it reveals nothing about the true stock beyond the tank. Stocks
and levels are test inputs drawn by Hypothesis."""

from hypothesis import given, settings
from hypothesis import strategies as st
from test_engine_vs_blueprint import FULL
from test_record import ROLES, kelvara_game

from fairflow_engine import AUTHORITY, observed_stock, resolve_season
from fairflow_engine.aquifer import pump_cap

BASIN = FULL.basin
Q = BASIN.aquifer


@settings(max_examples=200, deadline=None)
@given(stock=st.floats(Q.reserve, Q.initial), farm=st.integers(0, 2), share=st.floats(0, 1))
def test_a_previewed_level_resolves_the_same_for_every_stock_behind_the_same_tank_level(stock, farm, share):
    seen = observed_stock(BASIN, stock)
    limit = max(0.0, seen - Q.reserve)
    k = min(pump_cap(BASIN, stock, FULL.schemes[farm]), limit) * share
    pumps = [0.0, 0.0, 0.0]
    pumps[farm] = k
    params = dict(FULL.lenses)["proportional"]

    def preview(b):
        r = resolve_season(FULL.schemes, BASIN, FULL.inflow["normal"], b, "proportional", params, pumps, FULL.scoring)
        return r["Y"][farm], r["dL"][farm]

    assert preview(stock) == preview(seen)  # the true stock and its observed level give the same preview


def test_levels_above_the_public_limit_carry_no_preview():
    g = kelvara_game(gameLength=(5, 5))
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "close_vote")
    for e in (e for e in g.events if e["type"] == "private.opened"):
        p = e["payload"]
        assert p["previewLimit"] == max(0.0, observed_stock(BASIN, Q.initial) - Q.reserve)
        for o in p["options"]:
            assert (o["points"] is None) == (o["pumps"] > p["previewLimit"] + 1e-9)
    assert {e["payload"]["role"] for e in g.events if e["type"] == "private.opened"} == set(ROLES)
