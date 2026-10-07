# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Season Record (§6.2): rules, sealing, projections, audit. The setup is read from the blueprint and the registry;
nonces and the clock are test inputs."""

import copy
import hashlib
import json

import blueprint as bp
import pytest
from test_engine_vs_blueprint import BASIN, INFLOW, LENSES, SCHEMES, SCORING, lens_params

from fairflow_engine import (
    AUTHORITY,
    WHATEVER_WORKS,
    Game,
    GameSetup,
    Rejection,
    audit,
    draw_secrets,
    project,
    replay,
    verify_reveal,
)

SECTION = bp.section("### 2.2 Parameters and grounding")
DECK = dict(zip(["wet", "normal", "dry"], bp.grab(r"deck NUM W / NUM N / NUM D", SECTION), strict=True))
T_MIN, T_MAX = bp.grab(r"Uniform\{NUM, NUM\}", SECTION)
DEFAULT_LENS = json.loads((bp.ROOT / "packages" / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))[
    "defaultLens"
]
ROLES = [s.id for s in SCHEMES]
SEALED_KEYS = {"W", "A", "Y", "dL", "P", "pumpsBy", "pumpCost", "L"}


def setup(**over) -> GameSetup:
    base = dict(
        schemes=tuple(SCHEMES),
        basin=BASIN,
        inflow=dict(INFLOW),
        deck={k: int(v) for k, v in DECK.items()},
        gameLength=(int(T_MIN), int(T_MAX)),
        scoring=SCORING,
        lenses=tuple((lens, lens_params(lens)) for lens in LENSES),
        defaultLens=DEFAULT_LENS,
        floorRules=("proportional", "cea", "cel", "talmud", "capability"),
    )
    return GameSetup(**{**base, **over})


def clock():
    n = iter(range(10**6))
    return lambda: f"2026-10-05T10:00:{next(n):06d}Z"


def nonce(i: int) -> str:
    return hashlib.sha256(f"test-{i}".encode()).hexdigest()[:32]


def new_game(i=0, **over) -> Game:
    g = Game.create(setup(**over), f"g{i}", "room", {"appVersion": "test", "engineVersion": "test"}, clock(), nonce(i))
    for role in [*ROLES, AUTHORITY]:
        g.submit(role, "join", deviceHash=f"h-{role}", consentGiven=True, presurveyComplete=True)
    return g


def play_season(g: Game, lenses=("proportional", "utilitarian"), votes=None, pumps=None):
    g.submit(AUTHORITY, "start_season")
    for lens in lenses:
        g.submit(AUTHORITY, "propose", lens=lens)
    for role, lens in (votes or {r: lenses[0] for r in ROLES}).items():
        g.submit(role, "vote", lens=lens)
    g.submit(AUTHORITY, "close_vote")
    for role in ROLES:
        g.submit(role, "commit", pumps=(pumps or {}).get(role, 0.0))


def play_game(g: Game, pumps=None):
    while replay(g.events).phase != "ended":
        play_season(g, pumps=pumps)
    return g


def keys_in(obj) -> set:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(keys_in(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(keys_in(v) for v in obj)) if obj else set()
    return set()


def test_full_game_ends_after_T_seasons_reveals_and_audits():
    g = play_game(new_game(), pumps={"A": BASIN.pump.cap})
    ended = g.events[-1]
    assert ended["type"] == "game.ended" and ended["payload"]["seasonsPlayed"] == g.secrets.T
    assert verify_reveal(g.events[0], ended)
    assert audit(g.setup, g.events) == []


def test_game_length_and_deck():
    """§3.3 'T ∈ {5, 6}, each 0.50 ± 0.05; deck … always yields a dry season'. The blueprint says 100 nonces, but a fair
    draw of 100 misses ±0.05 about a quarter of the time (finding for the science reviewer); the test keeps the
    blueprint's share and tolerance and uses enough nonces that a fair draw fails with probability < 0.1 %."""
    from scipy.stats import binom

    share, tol = bp.grab(r"each NUM ± NUM", bp.BLUEPRINT)

    def false_alarm(n):
        return 1 - (binom.cdf((share + tol) * n, n, share) - binom.cdf((share - tol) * n - 1, n, share))

    n = next(m for m in range(100, 100_000, 100) if false_alarm(m) < 1e-3)  # smallest sample that rarely misfires
    draws = [draw_secrets(setup(), nonce(i)) for i in range(n)]
    assert {d.T for d in draws} <= {int(T_MIN), int(T_MAX)}
    for t in (int(T_MIN), int(T_MAX)):
        assert abs(sum(d.T == t for d in draws) / n - share) <= tol + 1e-9
    assert all("dry" in d.deckOrder[: d.T] for d in draws)


def test_privacy_projection_before_debrief():
    """§9.1 and ADR 0004: before the debrief the public view of a season holds only the in-play fields — no per-scheme
    figure and nothing computed on actual use."""
    from fairflow_engine.record import PUBLIC_RESULT_FIELDS

    g = play_game(new_game(), pumps={"A": BASIN.pump.cap})
    public = project(g.events, "public")
    assert not keys_in(public) & SEALED_KEYS
    for e in public:
        if e["type"] == "season.resolved":
            assert set(e["payload"]["public"]) == set(PUBLIC_RESULT_FIELDS) and "sealed" not in e["payload"]
    assert not any(e["type"] == "action.played" for e in public)
    assert all("pumpsTotal" in e["payload"]["public"] for e in public if e["type"] == "season.resolved")
    mine = project(g.events, "A")
    assert all(e["payload"]["self"]["P"] == e["payload"]["self"]["P"] for e in mine if e["type"] == "season.resolved")
    assert all(e["actor"] == "A" for e in mine if e["type"] == "action.played")


def test_debrief_per_player_choice():
    """R19: perPlayer = true opens pumpsBy; false keeps every per-scheme figure sealed in every projection."""
    for per_player in (True, False):
        g = play_game(new_game(), pumps={"A": BASIN.pump.cap})
        g.submit(AUTHORITY, "open_debrief", perPlayer=per_player)
        public = project(g.events, "public")
        assert ("pumpsBy" in keys_in(public)) is per_player
        if not per_player:
            assert not keys_in(public) & SEALED_KEYS


def test_rejections_leave_the_record_unchanged():
    g = new_game()

    def refused(actor, intent, **args):
        before = copy.deepcopy(g.events)
        with pytest.raises(Rejection):
            g.submit(actor, intent, **args)
        assert g.events == before

    refused(AUTHORITY, "close_vote")  # wrong phase (lobby)
    refused("A", "start_season")  # not the Authority
    refused(AUTHORITY, "fly")  # unknown intent
    g.submit(AUTHORITY, "start_season")
    refused("A", "vote", lens="talmud")  # not proposed
    refused("A", "commit", pumps=0.0)  # wrong phase (vote)
    refused(AUTHORITY, "vote", lens="proportional")  # the Authority does not vote
    g.submit(AUTHORITY, "propose", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    g.submit("A", "commit", pumps=0.0)
    for actor, args in (("A", {"pumps": 0.0}), ("B", {"pumps": BASIN.pump.cap * 2})):
        before = copy.deepcopy(g.events)
        with pytest.raises(Rejection):
            g.submit(actor, "commit", **args)
        assert g.events == before


def test_timeout_applies_default_then_previous_lens():
    """R8: expiry with no proposal applies the previous season's lens (the scenario's default in season 1), byTimeout."""
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "close_vote")
    chosen = [e for e in g.events if e["type"] == "lens.chosen"][-1]["payload"]
    assert (chosen["lens"], chosen["byTimeout"]) == (DEFAULT_LENS, True)
    for r in ROLES:
        g.submit(r, "commit", pumps=0.0)
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="talmud")
    g.submit("A", "vote", lens="talmud")
    g.submit(AUTHORITY, "close_vote")
    for r in ROLES:
        g.submit(r, "commit", pumps=0.0)
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "close_vote")
    assert [e for e in g.events if e["type"] == "lens.chosen"][-1]["payload"]["lens"] == "talmud"


def test_tie_goes_to_the_authority():
    g = new_game()
    g.submit(AUTHORITY, "start_season")
    for lens in ("egalitarian", "capability"):
        g.submit(AUTHORITY, "propose", lens=lens)
    g.submit("A", "vote", lens="egalitarian")
    g.submit("B", "vote", lens="capability")
    g.submit(AUTHORITY, "close_vote")
    assert replay(g.events).phase == "tiebreak"
    with pytest.raises(Rejection):
        g.submit(AUTHORITY, "break_tie", lens="talmud")
    g.submit(AUTHORITY, "break_tie", lens="capability")
    assert replay(g.events).lens == "capability"


@pytest.mark.parametrize(
    "votes,expected",
    [
        ({}, ("whatever_works", "proportional")),
        ({"A": "cea", "B": "cea", "C": "cel"}, ("cea", "cea")),
        ({"A": WHATEVER_WORKS}, (WHATEVER_WORKS, "proportional")),
    ],
)
def test_floor_vote_when_floors_exceed_the_water(votes, expected):
    """ADR 0003. Inflows here are test inputs chosen so that the sufficientarian floors cannot all be met."""
    floor = lens_params("sufficientarian").floor
    short = BASIN.reserve + 0.8 * sum(floor * s.demandMm3 for s in SCHEMES)
    g = new_game(inflow={card: short for card in INFLOW})
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="sufficientarian")
    g.submit(AUTHORITY, "close_vote")
    assert replay(g.events).phase == "floor_vote"
    for role, rule in votes.items():
        g.submit(role, "floor_vote", rule=rule)
    g.submit(AUTHORITY, "close_floor_vote")
    fr = [e for e in g.events if e["type"] == "lens.floorRule"][-1]["payload"]
    assert (fr["rule"], fr["applied"]) == expected and fr["byTimeout"] == (not votes)
    for r in ROLES:
        g.submit(r, "commit", pumps=0.0)
    assert audit(g.setup, g.events) == []


def test_timebox_ends_after_the_current_season_and_still_reveals():
    g = new_game()
    play_season(g)
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "timebox", sessionMinute=80)
    g.submit(AUTHORITY, "propose", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    for r in ROLES:
        g.submit(r, "commit", pumps=0.0)
    ended = g.events[-1]
    assert ended["type"] == "game.ended" and ended["payload"]["truncated"] and ended["payload"]["seasonsPlayed"] == 2
    assert verify_reveal(g.events[0], ended) and audit(g.setup, g.events) == []
    with pytest.raises(Rejection):
        g.submit(AUTHORITY, "start_season")


def test_tampering_is_detected():
    g = play_game(new_game(), pumps={"B": BASIN.pump.cap})
    forged = copy.deepcopy(g.events)
    resolved = next(e for e in forged if e["type"] == "season.resolved")
    resolved["payload"]["public"]["pumpsTotal"] += 1
    assert audit(g.setup, forged)
    forged = copy.deepcopy(g.events)
    forged[-1]["payload"]["T"] = 3 if forged[-1]["payload"]["T"] != 3 else 4
    assert not verify_reveal(forged[0], forged[-1])


def test_replay_reproduces_the_record():
    """§9.1 replay invariance: the same intents with the same nonce give the same record."""
    a = play_game(new_game(5), pumps={"C": BASIN.pump.cap})
    b = play_game(new_game(5), pumps={"C": BASIN.pump.cap})
    assert a.events == b.events


def test_audit_reports_a_numpy_version_change_instead_of_assuming():
    """NumPy Generator streams can change between feature releases; the deck/T draw is only re-derivable under the
    NumPy recorded at game.created, and audit() says so rather than passing silently."""
    g = play_game(new_game())
    assert audit(g.setup, g.events) == []
    moved = copy.deepcopy(g.events)
    moved[0]["payload"]["runtime"]["numpy"] = "0.0.0"
    assert any("cannot be re-derived" in p for p in audit(g.setup, moved))


def test_season_opens_with_engine_previews_of_every_enabled_lens():
    """S4 draws share-bars from the engine: each enabled lens's allocation and share of need, in card order."""
    from fairflow_engine import allocate

    g = new_game()
    g.submit(AUTHORITY, "start_season")
    climate = g.events[-1]["payload"]
    previews = climate["previews"]
    assert [p["lens"] for p in previews] == [lens for lens, _ in g.setup.lenses]
    for p, (lens, params) in zip(previews, g.setup.lenses, strict=True):
        assert p["Q"] == list(allocate(lens, g.setup.schemes, climate["allocable"], params, g.setup.scoring.survivalFloor).Q)
        assert all(abs(a - q / s.demandMm3) <= 1e-6 for a, q, s in zip(p["shareOfNeed"], p["Q"], g.setup.schemes, strict=True))
    assert all(e["visibility"] == "public" for e in g.events if e["type"] == "season.climate")
