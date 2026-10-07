# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Property-based tests (Hypothesis): §9.1 properties and the integrity of the Season Record under arbitrary sequences of
intents. Hypothesis searches for counterexamples and shrinks them; the generated values are test inputs, not model
values. Model parameters come from the registry."""

import copy
from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from test_engine_vs_blueprint import BASIN, LENSES, SCORING, lens_params
from test_properties import max_slope
from test_record import ROLES, new_game

from fairflow_engine import (
    AUTHORITY,
    FLOOR_RULES,
    WHATEVER_WORKS,
    Rejection,
    Scheme,
    allocate,
    audit,
    project,
    replay,
    resolve_season,
    value_of,
)

FLOOR = SCORING.survivalFloor
positive = st.floats(min_value=0.5, max_value=12, allow_nan=False)


@st.composite
def schemes(draw):
    n = draw(st.integers(min_value=3, max_value=5))
    return [
        Scheme(
            id=str(i),
            name=str(i),
            seat=i + 1,
            demandMm3=draw(positive),
            capacityT=draw(st.floats(300, 8000)),
            ky=draw(st.floats(0.4, 1.4)),
            beta=draw(st.floats(0.4, 1.0)),
            people=draw(st.floats(5, 3000)),
            kappa=draw(st.floats(0.5, 2)),
            price=draw(st.floats(0.3, 3)),
            areaHa=draw(st.floats(50, 1500)),
        )
        for i in range(n)
    ]


@settings(max_examples=200, deadline=None)
@given(s=schemes(), fraction=st.floats(0, 1.3), lens=st.sampled_from(LENSES), rule=st.sampled_from(sorted(FLOOR_RULES)))
def test_allocation_is_feasible_and_complete(s, fraction, lens, rule):
    """§9.1: Σ Q = min(AW, Σ D) and 0 ≤ Q_i ≤ D_i for every lens and every ADR 0003 floor rule."""
    D = [x.demandMm3 for x in s]
    AW = fraction * sum(D)
    Q = allocate(lens, s, AW, replace(lens_params(lens), floorScaling=rule), FLOOR).Q
    assert abs(sum(Q) - min(AW, sum(D))) <= 1e-5
    assert all(0 <= q <= d + 1e-6 for q, d in zip(Q, D, strict=True))


@settings(max_examples=150, deadline=None)
@given(s=schemes(), fraction=st.floats(0, 1))
def test_utilitarian_is_never_beaten_by_another_lens(s, fraction):
    """§9.1 maximiser optimality: every other lens's allocation is feasible, so none may produce more value."""
    AW = fraction * sum(x.demandMm3 for x in s)

    def value(Q):
        return sum(value_of(x, q, FLOOR) for x, q in zip(s, Q, strict=True))

    best = value(allocate("utilitarian", s, AW, lens_params("utilitarian"), FLOOR).Q)
    rounding = len(s) * 0.5e-6 * max_slope(s)  # Q is rounded to 1e-6 at the event boundary (§7.2)
    for lens in LENSES:
        other = allocate(lens, s, AW, replace(lens_params(lens), floorScaling="proportional"), FLOOR).Q
        assert value(other) <= best + rounding


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    s=schemes(), fraction=st.floats(0.01, 1.3), stock_above=st.floats(0, 25), lens=st.sampled_from(LENSES), data=st.data()
)
def test_aquifer_balance_closes(s, fraction, stock_above, lens, data):
    """§9.1: B_{t+1} = max(B_res, B_t + surplus + r₀ + return flows − ΣP), and pumping never draws below B_res."""
    pumps = data.draw(st.lists(st.floats(0, BASIN.pump.cap), min_size=len(s), max_size=len(s)))
    stock = BASIN.aquifer.reserve + stock_above
    AW = fraction * sum(x.demandMm3 for x in s)
    r = resolve_season(
        s, BASIN, BASIN.reserve + AW, stock, lens, replace(lens_params(lens), floorScaling="cea"), pumps, SCORING
    )
    balance = stock + r["allocation"]["surplusToAquifer"] + BASIN.aquifer.naturalRecharge + r["returnFlow"] - r["pumpsTotal"]
    assert abs(r["stockNext"] - max(BASIN.aquifer.reserve, balance)) <= 1e-5
    assert r["pumpsTotal"] <= stock - BASIN.aquifer.reserve + 1e-6


class SeasonRecordMachine(RuleBasedStateMachine):
    """Arbitrary sequences of intents, by any actor, in any order: rejections leave the record unchanged; the record
    always replays; the public view never carries a sealed field before the debrief; a finished game audits clean."""

    def __init__(self):
        super().__init__()
        self.game = new_game()

    def _try(self, actor, intent, **args):
        before = copy.deepcopy(self.game.events)
        try:
            self.game.submit(actor, intent, **args)
        except Rejection:
            assert self.game.events == before

    actors = st.sampled_from([*ROLES, AUTHORITY])

    @rule()
    def start(self):
        self._try(AUTHORITY, "start_season")

    @rule(actor=actors, lens=st.sampled_from([*LENSES, "not_a_lens"]))
    def propose(self, actor, lens):
        self._try(actor, "propose", lens=lens)

    @rule(actor=actors, lens=st.sampled_from(LENSES))
    def vote(self, actor, lens):
        self._try(actor, "vote", lens=lens)

    @rule(actor=actors)
    def close_vote(self, actor):
        self._try(actor, "close_vote")

    @rule(lens=st.sampled_from(LENSES))
    def break_tie(self, lens):
        self._try(AUTHORITY, "break_tie", lens=lens)

    @rule(actor=actors, rule_=st.sampled_from([*sorted(FLOOR_RULES), WHATEVER_WORKS]))
    def floor_vote(self, actor, rule_):
        self._try(actor, "floor_vote", rule=rule_)

    @rule()
    def close_floor_vote(self):
        self._try(AUTHORITY, "close_floor_vote")

    @rule(actor=actors, pumps=st.floats(-1, 4), action=st.sampled_from([None, "orchard", "drip", "expand", "steal"]))
    def commit(self, actor, pumps, action):
        self._try(actor, "commit", pumps=pumps, action=action)

    @rule(minute=st.floats(0, 120))
    def timebox(self, minute):
        self._try(AUTHORITY, "timebox", sessionMinute=minute)

    @invariant()
    def record_replays_and_stays_sealed(self):
        state = replay(self.game.events)
        assert state.season <= self.game.secrets.T
        public = project(self.game.events, "public")
        assert not any(e["type"] == "action.played" for e in public)
        assert all("sealed" not in e["payload"] for e in public if e["type"] == "season.resolved")
        assert not any(e["type"] in ("private.opened", "goal.result") for e in public)

    @invariant()
    def finished_games_audit_clean(self):
        if replay(self.game.events).phase == "ended":
            assert audit(self.game.setup, self.game.events) == []


SeasonRecordMachine.TestCase.settings = settings(max_examples=60, stateful_step_count=60, deadline=None)
TestSeasonRecord = SeasonRecordMachine.TestCase


@settings(max_examples=50, deadline=None)
@given(s=schemes(), lens=st.sampled_from(LENSES))
def test_no_renewable_supply_is_refused_not_crashed(s, lens):
    """Found by Hypothesis: with AW = 0 and r₀ = 0 the sustainability ratio is undefined (division by zero). The engine
    must refuse such a season with a clear ValueError, never crash or return a made-up value."""
    import pytest

    basin = replace(BASIN, aquifer=replace(BASIN.aquifer, naturalRecharge=0.0))
    with pytest.raises(ValueError, match="no renewable supply"):
        resolve_season(
            s, basin, basin.reserve, 20, lens, replace(lens_params(lens), floorScaling="cea"), [0.0] * len(s), SCORING
        )
