# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2 — the Season Record: an append-only event log with a visibility class per event (or per field),
driven by intents that the engine validates (R1–R20, without modules M2–M6 yet).

Clients submit intents; the engine either rejects one (typed `Rejection`, state unchanged) or appends events. Every
number in an event is computed here by the engine, never by a client. The game length T and the deck order are drawn
from a secret nonce, committed by SHA-256 at creation and revealed at `game.ended` (§4.1 R4, §7.2)."""

from __future__ import annotations

import copy
import hashlib
import re
import secrets as _secrets
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from importlib.metadata import PackageNotFoundError, version
from itertools import pairwise
from typing import Any, Literal, cast

import numpy as np
import scipy

from .allocate import allocate
from .aquifer import pump_cost_per_mm3
from .indicators import adequacy_band, efficiency_band, equity_band
from .model import Basin, LensId, LensParams, Scheme, Scoring, round6
from .season import SeasonResult, resolve_season, verdict
from .welfare import pwf_ede

Visibility = Literal["public", "self", "sealed", "mixed"]
Event = dict[str, Any]  # one Season Record entry (§6.2)
AUTHORITY = "authority"
WHATEVER_WORKS = "whatever_works"  # ADR 0003: the "whatever works" option
CROP_FAILURE_RUN = 2  # §2.4 "A ≤ 0.5 in two consecutive seasons is crop failure"
TUTORIAL_LENSES = ("proportional", "utilitarian")  # R3 season 0: "two lenses (proportional, utilitarian)"
TUTORIAL_CARD = "normal"  # R3 season 0: "normal year"
REVIEW_PARTS = (1, 2, 3)  # §5.2 S10 "Parts 1–3 of the review form"
REVIEW_ITEM = re.compile(r"[a-z0-9_.-]{1,40}")  # item ids come from content/review-form.json
ONCE_PER_GAME = ("orchard", "drip")  # §4.3 Orchard "once", Drip "once"; Expand "repeatable"
SCHEME_STATE = ("demandMm3", "capacityT", "price", "beta", "areaHa")  # what actions change (§2.2, §4.3)

# §6.2 as amended by ADR 0004: during play only these are public; every figure computed on actual use is sealed
# until the debrief (each one, with the public allocation, lets the table solve for individual pumping).
PUBLIC_RESULT_FIELDS = (
    "allocable",
    "pumpsTotal",
    "observedStockNext",
    "aquiferFull",
    "inflowLossNext",
    "asAllocated",
    "sustainabilityBand",
)
SEALED_RESULT_FIELDS = (
    "pumpCost",
    "P",
    "W",
    "A",
    "Y",
    "dL",
    "stockNext",
    "spill",
    "returnFlow",
    "ePJ",
    "eSE",
    "gini",
    "giniCorrected",
    "F",
    "S",
    "triangle",
    "welfare",
)


def with_state(x: Scheme, v: Mapping[str, float]) -> Scheme:
    """A scheme with the parameters in force this season (the SCHEME_STATE fields)."""
    return replace(
        x, demandMm3=v["demandMm3"], capacityT=v["capacityT"], price=v["price"], beta=v["beta"], areaHa=v["areaHa"]
    )


class Rejection(Exception):
    """An intent that the rules do not allow; the record is left unchanged (§7.1: applyEvent is total)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class GameSetup:
    """Everything a game needs from its scenario. All values come from the scenario or the registry."""

    schemes: tuple[Scheme, ...]
    basin: Basin
    inflow: dict[str, float]  # absolute inflow per card (§2.2)
    deck: dict[str, int]  # cards per type, e.g. from scenario basin.deck
    gameLength: tuple[int, int]  # (min, max), T ~ Uniform{min..max}
    scoring: Scoring
    lenses: tuple[tuple[LensId, LensParams], ...]  # enabled lenses in card order
    defaultLens: LensId
    floorRules: tuple[str, ...]  # ADR 0003 options offered (keys of FLOOR_RULES)
    actions: Mapping[str, Mapping[str, float]]  # Module 1 token costs and factors (registry, §2.2 and §4.3)
    goals: Mapping[str, tuple[str, float]]  # scheme id → (private goal kind, threshold) (R15, scenario privateGoal)
    authorityMaxMeanPumping: float  # R15 "average pumping ≤ 2 Mm³/season" (registry)
    bands: Mapping[str, tuple[float, float]]  # equity, efficiency and adequacy band edges (§2.2, registry)


@dataclass
class Secrets:
    """Held by the engine host only (the relay in room mode, the device in table mode); revealed at game.ended."""

    nonce: str
    T: int
    deckOrder: list[str]


def runtime_versions() -> dict[str, str]:
    """Versions that determine a record's numbers: the engine, and NumPy (whose Generator streams can change between
    feature releases, so the nonce → deck/T draw is only reproducible under the same NumPy) and SciPy (HiGHS)."""
    try:
        engine = version("fairflow-engine")
    except PackageNotFoundError:  # running from a source checkout without installation
        engine = "unknown"
    return {"fairflowEngine": engine, "numpy": np.__version__, "scipy": scipy.__version__}


def commitment(nonce: str, value: str) -> str:
    """SHA-256 commitment over the secret nonce and a value (§4.1 R4)."""
    return hashlib.sha256(f"{nonce}:{value}".encode()).hexdigest()


def draw_secrets(setup: GameSetup, nonce: str) -> Secrets:
    """T ~ Uniform{min..max} and a shuffled deck, both drawn from an RNG seeded by the nonce (§7.2)."""
    rng = np.random.default_rng(int(nonce, 16))  # layout: the nonce is a hex string
    lo, hi = setup.gameLength
    T = int(rng.integers(lo, hi + 1))
    cards = [card for card in ("wet", "normal", "dry") for _ in range(setup.deck.get(card, 0))]
    if len(cards) < hi:
        raise ValueError(f"deck has {len(cards)} cards but the game may last {hi} seasons")
    return Secrets(nonce=nonce, T=T, deckOrder=[str(c) for c in rng.permutation(cards)])


def verify_reveal(created: Event, ended: Event) -> bool:
    """Anyone can check the revealed T and deck against the commitments made at creation."""
    c, e = created["payload"]["commitments"], ended["payload"]
    return bool(
        commitment(e["nonce"], str(e["T"])) == c["gameLength"]
        and commitment(e["nonce"], ",".join(e["deckOrder"])) == c["deckOrder"]
    )


@dataclass
class State:
    """What the events imply. Rebuilt by replaying the record (`replay`); never stored."""

    phase: str = "lobby"  # lobby → vote → [tiebreak] → [floor_vote] → private → reveal → … → ended
    season: int = 0
    stock: float = 0.0
    inflowLoss: float = 0.0
    players: dict[str, dict[str, Any]] = field(default_factory=dict)
    proposals: list[str] = field(default_factory=list)
    votes: dict[str, str] = field(default_factory=dict)
    floorVotes: dict[str, str] = field(default_factory=dict)
    lens: LensId | None = None
    previousLens: LensId | None = None
    floorRule: str | None = None
    allocation: dict[str, Any] | None = None
    climate: dict[str, Any] | None = None
    committed: set[str] = field(default_factory=set)
    livelihood: dict[str, float] = field(default_factory=dict)
    lowRun: dict[str, int] = field(default_factory=dict)  # consecutive seasons at A ≤ survival floor
    cropFailure: dict[str, bool] = field(default_factory=dict)
    scores: list[float] = field(default_factory=list)
    timeboxed: bool = False
    debrief: dict[str, Any] | None = None
    schemes: dict[str, dict[str, float]] = field(default_factory=dict)  # parameters in force this season (public)
    pendingActions: dict[str, str] = field(default_factory=dict)  # played this season, in force from the next
    used: dict[str, list[str]] = field(default_factory=dict)  # every action each scheme has played


def apply_event(state: State, event: Event) -> State:
    """Pure fold step: state after `event`. Numbers are taken from the event, never recomputed here."""
    s = copy.deepcopy(state)
    p, kind = event["payload"], event["type"]
    if kind == "game.created":
        s.stock = p["aquiferInitial"]
        s.livelihood = {r: 0.0 for r in p["schemeRoles"]}
        s.lowRun = {r: 0 for r in p["schemeRoles"]}
        s.cropFailure = {r: False for r in p["schemeRoles"]}
        s.schemes = {v["id"]: {k: v[k] for k in SCHEME_STATE} for v in p["schemes"]}
        s.used = {r: [] for r in p["schemeRoles"]}
    elif kind == "player.joined":
        s.players[p["role"]] = p
    elif kind == "season.climate":
        s.season, s.climate, s.phase = event["season"], p, "vote"
        s.schemes = {v["id"]: {k: v[k] for k in SCHEME_STATE} for v in p["schemes"]}
        s.pendingActions = {}
        s.proposals, s.votes, s.floorVotes, s.committed = [], {}, {}, set()
        s.lens, s.floorRule, s.allocation = None, None, None
    elif kind == "lens.proposed":
        s.proposals.append(p["lens"])
    elif kind == "lens.voted":
        s.votes[p["voter"]] = p["lens"]
    elif kind == "lens.tied":
        s.phase = "tiebreak"
    elif kind == "lens.chosen":
        s.lens, s.previousLens = p["lens"], p["lens"]
        s.phase = "floor_vote" if p.get("floorVoteNeeded") else "private"
    elif kind == "lens.floorVoted":
        s.floorVotes[p["voter"]] = p["rule"]
    elif kind == "lens.floorRule":
        s.floorRule, s.phase = p["applied"], "private"
    elif kind == "allocation.issued":
        s.allocation = p
    elif kind == "action.played":
        s.committed.add(p["role"])
        if p.get("action"):
            s.pendingActions[p["role"]] = p["action"]
            s.used.setdefault(p["role"], []).append(p["action"])
    elif kind == "season.resolved":
        pub, sealed = p["public"], p["sealed"]
        s.stock, s.inflowLoss, s.phase = sealed["stockNext"], pub["inflowLossNext"], "reveal"
        s.scores.append(sealed["triangle"]["score"])
        for role, L, run, failed in zip(sealed["roles"], sealed["L"], sealed["lowRun"], sealed["cropFailure"], strict=True):
            s.livelihood[role], s.lowRun[role], s.cropFailure[role] = L, run, failed
    elif kind == "tutorial.resolved":  # R3: season 0 is practice; nothing it computed carries into the game
        s.phase, s.previousLens = "reveal", None
    elif kind == "game.timeboxed":
        s.timeboxed = True
    elif kind == "game.ended":
        s.phase = "ended"
    elif kind == "debrief.opened":
        s.debrief = p
    return s


def replay(events: Sequence[Event]) -> State:
    """state = events.reduce(applyEvent, initialState) (§6.2)."""
    state = State()
    for e in events:
        state = apply_event(state, e)
    return state


class Game:
    """The engine host's view of one game: the record plus the secrets. `submit` is the only way in."""

    def __init__(self, setup: GameSetup, secrets: Secrets, events: list[Event], clock: Callable[[], str]):
        self.setup, self.secrets, self.events, self.clock = setup, secrets, events, clock

    # ---- creation ------------------------------------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        setup: GameSetup,
        game_id: str,
        mode: str,
        versions: dict[str, str],
        clock: Callable[[], str],
        nonce: str | None = None,
    ) -> Game:
        nonce = nonce or _secrets.token_hex(16)  # layout: 128-bit secret nonce
        sec = draw_secrets(setup, nonce)
        game = cls(setup, sec, [], clock)
        game._emit(
            "game.created",
            "engine",
            "public",
            {
                "gameId": game_id,
                "mode": mode,
                **versions,
                "schemeRoles": [s.id for s in setup.schemes],
                "schemes": [{"id": s.id, **{k: getattr(s, k) for k in SCHEME_STATE}} for s in setup.schemes],
                "aquiferInitial": setup.basin.aquifer.initial,
                "commitments": {
                    "gameLength": commitment(nonce, str(sec.T)),
                    "deckOrder": commitment(nonce, ",".join(sec.deckOrder)),
                },
                "lenses": [lens for lens, _ in setup.lenses],
                "defaultLens": setup.defaultLens,
                "floorRules": list(setup.floorRules),
                "runtime": runtime_versions(),
            },
        )
        return game

    @property
    def state(self) -> State:
        return replay(self.events)

    # ---- intents -------------------------------------------------------------------------------------------------
    def submit(self, actor: str, intent: str, **args: Any) -> list[Event]:
        """Validate an intent and append the events it causes. Raises Rejection and leaves the record unchanged."""
        before = len(self.events)
        try:
            handler = getattr(self, f"_on_{intent}", None)
            if handler is None:
                raise Rejection("unknown_intent", intent)
            handler(self.state, actor, **args)
        except Rejection:
            del self.events[before:]
            raise
        except TypeError as e:
            del self.events[before:]
            raise Rejection("bad_input", str(e)) from None
        except ValueError as e:  # the engine refused the computation (e.g. a missing parameter)
            del self.events[before:]
            raise Rejection("rejected", str(e)) from None
        return self.events[before:]

    def _scheme_roles(self) -> list[str]:
        return [s.id for s in self.setup.schemes]

    def _need(self, cond: bool, code: str, message: str) -> None:
        if not cond:
            raise Rejection(code, message)

    def _as_lens(self, name: str) -> LensId:
        """A lens name from an intent or a tally, checked against the scenario's enabled lenses."""
        self._need(name in [lens for lens, _ in self.setup.lenses], "lens_not_enabled", name)
        return cast(LensId, name)

    def _climate(self, s: State) -> dict[str, Any]:
        if s.climate is None:
            raise Rejection("wrong_phase", "no season is open")
        return s.climate

    def _schemes(self, s: State) -> tuple[Scheme, ...]:
        """The schemes with the parameters in force this season (actions take effect from t+1, §2.2)."""
        return tuple(with_state(x, s.schemes[x.id]) if x.id in s.schemes else x for x in self.setup.schemes)

    def _after_actions(self, s: State) -> dict[str, dict[str, float]]:
        """Scheme parameters for the next season: last season's actions applied (§2.2, §4.3), rounded to 1e-6 (§7.2)."""
        out = {r: dict(v) for r, v in s.schemes.items()}
        for role, action in s.pendingActions.items():
            a, v = self.setup.actions[action], out[role]
            if action == "orchard":  # D × 1.3, p × 2
                v["demandMm3"] *= a["demandFactor"]
                v["price"] *= a["priceFactor"]
            elif action == "drip":  # D × 0.8 at constant K; β → 0.90
                v["demandMm3"] *= a["demandFactor"]
                v["beta"] = a["betaAfter"]
            elif action == "expand":  # area, D and K × 1.2
                for k in ("areaHa", "demandMm3", "capacityT"):
                    v[k] *= a["factor"]
            out[role] = {k: round6(x) for k, x in v.items()}
        return out

    def _chosen_lens(self, s: State) -> LensId:
        if s.lens is None:
            raise Rejection("wrong_phase", "no lens has been chosen this season")
        return s.lens

    def _on_join(self, s: State, actor: str, deviceHash: str, consentGiven: bool, presurveyComplete: bool) -> None:
        """R2, R3: a role is taken once; consent and pre-survey are recorded before the role is shown."""
        self._need(s.phase == "lobby", "wrong_phase", "players join before season 1")
        self._need(actor in [*self._scheme_roles(), AUTHORITY], "unknown_role", actor)
        self._need(actor not in s.players, "role_taken", actor)
        self._emit(
            "player.joined",
            actor,
            "public",
            {"role": actor, "deviceId": deviceHash, "consentGiven": consentGiven, "presurveyComplete": presurveyComplete},
        )

    def _on_start_tutorial(self, s: State, actor: str) -> None:
        """R3: season 0, a facilitated practice round before season 1: a normal year, two lenses (proportional,
        utilitarian), one practice private turn with pump cost 0 and no actions, nothing scored. The committed deck and
        length are untouched: season 1 still draws the first card."""
        self._need(actor == AUTHORITY, "not_authority", "only the Authority opens the tutorial")
        self._need(s.phase == "lobby", "wrong_phase", "the tutorial comes before season 1")
        self._need(set(self._scheme_roles()) <= set(s.players), "seats_empty", "every scheme role must be taken")
        lenses = self._tutorial_lenses()
        self._need(bool(lenses), "lens_not_enabled", "the tutorial needs the proportional or utilitarian lens")
        inflow = self.setup.inflow[TUTORIAL_CARD]
        allocable = max(0.0, inflow - self.setup.basin.reserve)
        schemes = self._schemes(s)
        self._emit(
            "season.climate",
            "engine",
            "public",
            {
                "card": TUTORIAL_CARD,
                "inflow": inflow,
                "reserve": self.setup.basin.reserve,
                "allocable": allocable,
                "schemes": [{"id": x.id, **{k: getattr(x, k) for k in SCHEME_STATE}} for x in schemes],
                "previews": [p for p in self._previews(allocable, schemes) if p["lens"] in lenses],
                "tutorial": True,
            },
            season=0,
        )

    def _tutorial_lenses(self) -> list[str]:
        return [name for name, _ in self.setup.lenses if name in TUTORIAL_LENSES]

    @staticmethod
    def _is_tutorial(s: State) -> bool:
        return s.climate is not None and bool(s.climate.get("tutorial"))

    def _basin(self, s: State) -> Basin:
        """The basin for this season's computation; in the tutorial pumping costs nothing (R3 "pump cost 0")."""
        return tutorial_basin(self.setup.basin) if self._is_tutorial(s) else self.setup.basin

    def _on_start_season(self, s: State, actor: str) -> None:
        """R6: the Authority opens the next season; the engine reveals the card and the allocable water."""
        self._need(actor == AUTHORITY, "not_authority", "only the Authority opens a season")
        self._need(s.phase in ("lobby", "reveal"), "wrong_phase", s.phase)
        self._need(not s.timeboxed and s.season < self.secrets.T, "game_over", "no further season")
        if s.phase == "lobby":
            self._need(set(self._scheme_roles()) <= set(s.players), "seats_empty", "every scheme role must be taken")
        season = s.season + 1
        card = self.secrets.deckOrder[season - 1]
        inflow = self.setup.inflow[card] - s.inflowLoss
        allocable = max(0.0, inflow - self.setup.basin.reserve)
        in_force = self._after_actions(s)
        schemes = tuple(with_state(x, in_force[x.id]) for x in self.setup.schemes)
        self._emit(
            "season.climate",
            "engine",
            "public",
            {
                "card": card,
                "inflow": inflow,
                "reserve": self.setup.basin.reserve,
                "allocable": allocable,
                "schemes": [{"id": x.id, **in_force[x.id]} for x in self.setup.schemes],
                "previews": self._previews(allocable, schemes),
            },
            season=season,
        )

    def _previews(self, allocable: float, schemes: tuple[Scheme, ...]) -> list[dict[str, Any]]:
        """S4: every enabled lens's allocation for this season, computed by the engine so the vote screen only draws it.
        Public: allocations are public (R17). Where the sufficientarian floors exceed the water, the preview uses the
        "whatever works" cut and says that the table would choose (ADR 0003)."""
        floor = self.setup.scoring.survivalFloor
        out = []
        for lens, params in self.setup.lenses:
            Q = list(allocate(lens, schemes, allocable, params, floor).Q)
            out.append(
                {
                    "lens": lens,
                    "Q": Q,
                    "shareOfNeed": [round6(q / s.demandMm3) for q, s in zip(Q, schemes, strict=True)],
                    "floorVoteNeeded": lens == "sufficientarian"
                    and sum(params.need("floor", lens) * x.demandMm3 for x in schemes) >= allocable,
                }
            )
        return out

    def _on_propose(self, s: State, actor: str, lens: str) -> None:
        """R7: lenses are proposed aloud; the record keeps lens and proposer."""
        self._need(s.phase == "vote", "wrong_phase", s.phase)
        self._need(lens in [name for name, _ in self.setup.lenses], "lens_not_enabled", lens)
        self._need(not self._is_tutorial(s) or lens in self._tutorial_lenses(), "lens_not_in_tutorial", lens)
        self._need(lens not in s.proposals, "already_proposed", lens)
        self._emit("lens.proposed", actor, "public", {"lens": lens, "proposer": actor}, season=s.season)

    def _on_vote(self, s: State, actor: str, lens: str) -> None:
        """R8: each scheme player votes for a proposed lens (the Authority taps the chip; the voter is the scheme)."""
        self._need(s.phase == "vote", "wrong_phase", s.phase)
        self._need(actor in self._scheme_roles(), "not_a_voter", actor)
        self._need(lens in s.proposals, "not_proposed", lens)
        self._emit("lens.voted", actor, "public", {"lens": lens, "voter": actor}, season=s.season)

    def _on_close_vote(self, s: State, actor: str) -> None:
        """R8: plurality wins; a tie goes to the Authority; no proposal at timer expiry applies the previous lens
        (the scenario's default lens in season 1), recorded as byTimeout."""
        self._need(actor == AUTHORITY, "not_authority", "only the Authority closes the vote")
        self._need(s.phase == "vote", "wrong_phase", s.phase)
        if not s.proposals:
            self._choose(s, s.previousLens or self.setup.defaultLens, tally={}, by_timeout=True)
            return
        tally = Counter(s.votes.values())
        if not tally:
            self._need(len(s.proposals) == 1, "no_votes", "votes needed to choose among several proposals")
            self._choose(s, self._as_lens(s.proposals[0]), tally={}, by_timeout=False)
            return
        top = max(tally.values())
        leaders = sorted(name for name, n in tally.items() if n == top)
        if len(leaders) > 1:
            self._emit("lens.tied", "engine", "public", {"leaders": leaders, "tally": dict(tally)}, season=s.season)
            return
        self._choose(s, self._as_lens(leaders[0]), tally=dict(tally), by_timeout=False)

    def _on_break_tie(self, s: State, actor: str, lens: str) -> None:
        self._need(actor == AUTHORITY, "not_authority", "only the Authority breaks a tie")
        self._need(s.phase == "tiebreak", "wrong_phase", s.phase)
        tied = next(e for e in reversed(self.events) if e["type"] == "lens.tied")["payload"]
        self._need(lens in tied["leaders"], "not_a_leader", lens)
        self._choose(s, self._as_lens(lens), tally=tied["tally"], by_timeout=False, tie_break=True)

    def _choose(self, s: State, lens: LensId, tally: dict[str, int], by_timeout: bool, tie_break: bool = False) -> None:
        floors_short = lens == "sufficientarian" and self._floors_exceed(s)
        self._emit(
            "lens.chosen",
            AUTHORITY if tie_break else "engine",
            "public",
            {"lens": lens, "tally": tally, "byTimeout": by_timeout, "tieBreak": tie_break, "floorVoteNeeded": floors_short},
            season=s.season,
        )
        if not floors_short:
            self._issue_allocation(lens, None, s)

    def _floors_exceed(self, s: State) -> bool:
        params = dict(self.setup.lenses)["sufficientarian"]
        floor = params.need("floor", "sufficientarian")
        return bool(sum(floor * x.demandMm3 for x in self._schemes(s)) >= self._climate(s)["allocable"])

    def _on_floor_vote(self, s: State, actor: str, rule: str) -> None:
        """ADR 0003: when the sufficientarian floors exceed the water, the table votes how to cut them."""
        self._need(s.phase == "floor_vote", "wrong_phase", s.phase)
        self._need(actor in self._scheme_roles(), "not_a_voter", actor)
        self._need(rule in self.setup.floorRules or rule == WHATEVER_WORKS, "rule_not_offered", rule)
        self._emit("lens.floorVoted", actor, "public", {"rule": rule, "voter": actor}, season=s.season)

    def _on_close_floor_vote(self, s: State, actor: str, tieBreak: str | None = None) -> None:
        """ADR 0003: plurality; a tie goes to the Authority (`tieBreak`); no votes, or "whatever works", is proportional."""
        self._need(actor == AUTHORITY, "not_authority", "only the Authority closes the vote")
        self._need(s.phase == "floor_vote", "wrong_phase", s.phase)
        tally = Counter(s.floorVotes.values())
        if not tally:
            rule, by_timeout = WHATEVER_WORKS, True
        else:
            top = max(tally.values())
            leaders = sorted(r for r, n in tally.items() if n == top)
            if len(leaders) > 1:
                if tieBreak is None or tieBreak not in leaders:
                    raise Rejection("tie", f"Authority must break the tie among {leaders}")
                rule = tieBreak
            else:
                rule = leaders[0]
            by_timeout = False
        applied = "proportional" if rule == WHATEVER_WORKS else rule
        self._emit(
            "lens.floorRule",
            "engine",
            "public",
            {"rule": rule, "applied": applied, "tally": dict(tally), "byTimeout": by_timeout},
            season=s.season,
        )
        self._issue_allocation("sufficientarian", applied, s)

    def _lens_params(self, lens: LensId, floor_rule: str | None) -> LensParams:
        params = dict(self.setup.lenses)[lens]
        if floor_rule is None:
            return params
        return LensParams(**{**params.__dict__, "floorScaling": floor_rule})

    def _issue_allocation(self, lens: LensId, floor_rule: str | None, s: State) -> None:
        """R9: the engine computes Q under the lens; surplus to the aquifer. Public."""
        r = self._resolve(s, lens, floor_rule, pumps=[0.0] * len(self.setup.schemes))
        self._emit(
            "allocation.issued",
            "engine",
            "public",
            {
                "lens": lens,
                "floorRule": floor_rule,
                "Q": r["allocation"]["Q"],
                "surplusToAquifer": r["allocation"]["surplusToAquifer"],
                "adequacyBands": [
                    adequacy_band(q / x.demandMm3, self.setup.bands["adequacy"])
                    for q, x in zip(r["allocation"]["Q"], self._schemes(s), strict=True)
                ],
            },
            season=s.season,
        )
        self._open_private_turns(s, lens, floor_rule)

    def _open_private_turns(self, s: State, lens: LensId, floor_rule: str | None) -> None:
        """S6 (R10): each scheme sees, privately, its pump cost and the engine's preview of every choice — harvest and
        points for 0..cap pump tokens, with and without each action still open to it. The preview assumes the others
        do not pump (pumping is rationed only when the stock runs short, §2.6)."""
        schemes = self._schemes(s)
        cap = self.setup.basin.pump.cap
        for i, x in enumerate(schemes):
            open_actions = [
                a
                for a in self.setup.actions
                if not self._is_tutorial(s) and not (a in ONCE_PER_GAME and a in s.used.get(x.id, []))
            ]
            options = []
            for k in range(int(cap) + 1):  # layout: whole pump tokens, 0..cap (R10)
                pumps = [0.0] * len(schemes)
                pumps[i] = float(k)
                r = self._resolve(s, lens, floor_rule, pumps)
                points = {"none": r["dL"][i]}
                points.update({a: round6(r["dL"][i] - self.setup.actions[a]["cost"]) for a in open_actions})
                options.append({"pumps": k, "yieldT": r["Y"][i], "points": points})
            self._emit(
                "private.opened",
                x.id,
                "self",
                {
                    "role": x.id,
                    "cap": cap,
                    "pumpCostPerMm3": round6(pump_cost_per_mm3(self._basin(s), s.stock, x.seat)),
                    "actions": {a: self.setup.actions[a]["cost"] for a in open_actions},
                    "options": options,
                    "assumes": "the other farms do not pump",
                },
                season=s.season,
            )

    def _on_commit(self, s: State, actor: str, pumps: float, action: str | None = None) -> None:
        """R10: each scheme commits its private turn (0..cap pumps). Sealed until the debrief."""
        self._need(s.phase == "private", "wrong_phase", s.phase)
        self._need(actor in self._scheme_roles(), "not_a_scheme", actor)
        self._need(actor not in s.committed, "already_committed", actor)
        self._need(0 <= pumps <= self.setup.basin.pump.cap, "pump_out_of_range", f"0..{self.setup.basin.pump.cap}")
        if action is not None:  # R10: at most one Action token
            self._need(not self._is_tutorial(s), "no_actions_in_tutorial", action)
            self._need(action in self.setup.actions, "unknown_action", action)
            self._need(not (action in ONCE_PER_GAME and action in s.used.get(actor, [])), "action_used", action)
        self._emit(
            "action.played",
            actor,
            "sealed",
            {"role": actor, "pumps": pumps, "action": action, "committedAt": self.clock()},
            season=s.season,
        )
        if s.committed | {actor} == set(self._scheme_roles()):
            self._resolve_season(replay(self.events))

    def _resolve(self, s: State, lens: LensId, floor_rule: str | None, pumps: list[float]) -> SeasonResult:
        return resolve_season(
            self._schemes(s),
            self._basin(s),
            self._climate(s)["inflow"],
            s.stock,
            lens,
            self._lens_params(lens, floor_rule),
            pumps,
            self.setup.scoring,
        )

    def _resolve_season(self, s: State) -> None:
        """R11: pumps drawn, rationed; W, Y, ΔL, dials; aquifer stepped. Mixed visibility (§6.2)."""
        roles = self._scheme_roles()
        plays = [e["payload"] for e in self.events if e["type"] == "action.played" and e["season"] == s.season]
        played = {pl["role"]: pl["pumps"] for pl in plays}
        action_cost = {pl["role"]: self.setup.actions[pl["action"]]["cost"] if pl.get("action") else 0.0 for pl in plays}
        pumps = [played[r] for r in roles]
        lens = self._chosen_lens(s)
        r = self._resolve(s, lens, s.floorRule, pumps)
        if self._is_tutorial(s):
            self._resolve_tutorial(s, roles, r)
            return
        floor = self.setup.scoring.survivalFloor
        low_run = [s.lowRun[role] + 1 if a <= floor else 0 for role, a in zip(roles, r["A"], strict=True)]
        failed = [s.cropFailure[role] or run >= CROP_FAILURE_RUN for role, run in zip(roles, low_run, strict=True)]
        # §2.4 ΔL = pY/100 − c_p P − c_action: the engine's dL holds the first two terms; the action cost is charged here
        L = [round6(s.livelihood[role] + d - action_cost[role]) for role, d in zip(roles, r["dL"], strict=True)]
        applied = [  # the parameters actually applied, with the table's floor rule (review E1)
            (name, self._lens_params(name, s.floorRule if name == "sufficientarian" else None))
            for name, _ in self.setup.lenses
        ]
        v = verdict(self._schemes(s), r["allocable"], r["W"], lens, r["pumpsTotal"], applied, floor)
        result: dict[str, Any] = dict(r)
        public = {k: result[k] for k in PUBLIC_RESULT_FIELDS}
        public["bands"] = {  # band words of the as-allocated dials (ADR 0004: computed on the public allocation)
            "ePJ": equity_band(r["asAllocated"]["ePJ"], self.setup.bands["equity"]),
            "eSE": equity_band(r["asAllocated"]["eSE"]["claimant"], self.setup.bands["equity"]),
            "F": efficiency_band(r["asAllocated"]["F"]["consumed"], self.setup.bands["efficiency"]),
        }
        sealed = {k: result[k] for k in SEALED_RESULT_FIELDS}
        sealed.update(
            {
                "roles": roles,
                "pumpsBy": dict(zip(roles, r["P"], strict=True)),
                "L": L,
                "lowRun": low_run,
                "cropFailure": failed,
                "cropFailureFlag": any(failed),
                "actionCost": [action_cost[role] for role in roles],
                # §2.4 ΔL in full, the season's change in L; dL omits the action cost (review E10)
                "points": [round6(d - action_cost[role]) for role, d in zip(roles, r["dL"], strict=True)],
                "verdict": {"voted": v["voted"], "satisfied": v["satisfied"], "pumpingGap": v["pumpingGap"]},
            }
        )
        self._emit("season.resolved", "engine", "mixed", {"public": public, "sealed": sealed}, season=s.season)
        after = replay(self.events)
        if after.season >= self.secrets.T or after.timeboxed:
            self._end(after)

    def _resolve_tutorial(self, s: State, roles: list[str], r: SeasonResult) -> None:
        """R3: the practice round's reveal, with the same visibility as a season; nothing is scored or carried over
        (livelihood, aquifer, crop-failure runs and the lens default stay as they were)."""
        result: dict[str, Any] = dict(r)
        sealed = {k: result[k] for k in SEALED_RESULT_FIELDS}
        sealed.update(
            {
                "roles": roles,
                "L": [s.livelihood[role] for role in roles],
                "cropFailure": [s.cropFailure[role] for role in roles],
                "points": list(r["dL"]),  # no actions in the tutorial, so ΔL = dL
            }
        )
        public = {k: result[k] for k in PUBLIC_RESULT_FIELDS}
        self._emit("tutorial.resolved", "engine", "mixed", {"public": public, "sealed": sealed}, season=0)

    def _on_timebox(self, s: State, actor: str, sessionMinute: float) -> None:
        """R20: the facilitator time-box ends play after the current season; T is still revealed."""
        self._need(actor == AUTHORITY, "not_authority", "only the facilitator time-boxes")
        self._need(s.phase not in ("ended",) and not s.timeboxed, "wrong_phase", s.phase)
        self._emit(
            "game.timeboxed", actor, "public", {"atSeason": s.season, "sessionMinute": sessionMinute}, season=s.season
        )
        if s.phase in ("lobby", "reveal"):
            self._end(replay(self.events))

    def _brief(self) -> dict[str, Any]:
        """The facilitator's debrief brief (§5.0), from public events only: the heaviest pumping season, the lens of each
        season and how often it changed, whether a floor vote was held."""
        resolved = [e for e in self.events if e["type"] == "season.resolved"]
        lenses = [e["payload"]["lens"] for e in self.events if e["type"] == "lens.chosen" and e["season"] > 0]
        heaviest = max(resolved, key=lambda e: e["payload"]["public"]["pumpsTotal"], default=None)
        return {
            "heaviestPumping": None
            if heaviest is None
            else {"season": heaviest["season"], "pumpsTotal": heaviest["payload"]["public"]["pumpsTotal"]},
            "lensBySeason": lenses,
            "lensChanges": sum(a != b for a, b in pairwise(lenses)),
            "floorVotes": sum(e["type"] == "lens.floorRule" for e in self.events),
        }

    def _goals(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """R15 private goals, judged within each scheme: the Authority's from public totals; each farm's from its own
        sealed results (it sees only its own, as a self event)."""
        resolved = [e for e in self.events if e["type"] == "season.resolved"]
        climates = {e["season"]: e["payload"] for e in self.events if e["type"] == "season.climate"}
        totals = [e["payload"]["public"]["pumpsTotal"] for e in resolved]
        mean = sum(totals) / len(totals) if totals else 0.0
        authority = {
            "maxMeanPumping": self.setup.authorityMaxMeanPumping,
            "meanPumping": round6(mean),
            "met": mean <= self.setup.authorityMaxMeanPumping,
        }
        farms = []
        for x in self.setup.schemes:
            kind, threshold = self.setup.goals[x.id]
            idx = [e["payload"]["sealed"]["roles"].index(x.id) for e in resolved]
            adequacy = [e["payload"]["sealed"]["A"][i] for e, i in zip(resolved, idx, strict=True)]
            if kind == "livelihood_share":  # cumulative livelihood ≥ threshold × the full-demand potential, Σ pK/100 (§2.4)
                in_force = [next(v for v in climates[e["season"]]["schemes"] if v["id"] == x.id) for e in resolved]
                potential = sum(v["price"] * v["capacityT"] / 100 for v in in_force)  # §2.4 ΔL = pY/100, full demand
                final = resolved[-1]["payload"]["sealed"]["L"][idx[-1]] if resolved else 0.0
                value = final / potential if potential else 0.0
                met = value >= threshold
            elif kind == "adequacy_floor":  # adequacy never below the threshold
                value, met = min(adequacy, default=0.0), all(a >= threshold for a in adequacy)
            elif kind == "adequacy_in_half_seasons":  # adequacy ≥ threshold in at least half the seasons
                value = float(sum(a >= threshold for a in adequacy))
                met = 2 * value >= len(adequacy)  # layout: "at least half"
            else:
                raise ValueError(f"unknown private goal kind {kind!r}")
            farms.append({"role": x.id, "kind": kind, "threshold": threshold, "value": round6(value), "met": met})
        return authority, farms

    def _end(self, s: State) -> None:
        sec = self.secrets
        authority, farms = self._goals()
        self._emit(
            "game.ended",
            "engine",
            "public",
            {
                "T": sec.T,
                "nonce": sec.nonce,
                "deckOrder": sec.deckOrder,
                "truncated": s.timeboxed or s.season < sec.T,
                "seasonsPlayed": s.season,
                "collectiveScore": round6(float(np.mean(s.scores))) if s.scores else 0.0,  # §7.2 rounding (review E9)
                "cropFailureFlag": any(s.cropFailure.values()),
                "brief": self._brief(),
                "authorityGoal": authority,
            },
            season=s.season,
        )
        for goal in farms:
            self._emit("goal.result", goal["role"], "self", goal, season=s.season)

    def _on_open_debrief(self, s: State, actor: str, perPlayer: bool) -> None:
        """R19: sealed fields become readable; perPlayer = false keeps pumpsBy sealed in every projection."""
        self._need(actor == AUTHORITY, "not_authority", "only the facilitator opens the debrief")
        self._need(s.phase == "ended" and s.debrief is None, "wrong_phase", s.phase)
        self._emit("debrief.opened", actor, "public", {"perPlayer": perPlayer}, season=s.season)
        self._emit("debrief.welfare", "engine", "public", debrief_welfare(self.setup, self.events), season=s.season)

    def _on_review_answer(self, s: State, actor: str, part: int, item: str, value: str) -> None:
        """S10: one answer of the review form (§5.4), private to its author in every projection, even after a per-player
        debrief. Answers may be revised; the latest per item counts."""
        self._need(actor in self._scheme_roles(), "not_a_player", "the review form is for the farms' players")
        self._need(s.phase == "ended", "wrong_phase", "the review follows the game")
        self._need(part in REVIEW_PARTS, "bad_input", f"part {part}")
        self._need(REVIEW_ITEM.fullmatch(item) is not None, "bad_input", "item id")
        self._need(isinstance(value, str), "bad_input", "an answer is text")  # its length is the server's limit
        self._emit("review.answer", actor, "self", {"part": part, "item": item, "value": value}, season=s.season)

    # ---- record --------------------------------------------------------------------------------------------------
    def _emit(
        self, kind: str, actor: str, visibility: Visibility, payload: dict[str, Any], season: int | None = None
    ) -> None:
        self.events.append(
            {
                "seq": len(self.events) + 1,
                "t": self.clock(),
                "season": season if season is not None else 0,
                "actor": actor,
                "type": kind,
                "payload": payload,
                "visibility": visibility,
            }
        )


def tutorial_basin(basin: Basin) -> Basin:
    """R3: the practice round's basin, identical except that pumping costs nothing ("pump cost 0")."""
    return replace(basin, pump=replace(basin.pump, costBase=0.0, costSlope=0.0))


# ---- debrief (S9, ADR 0003) --------------------------------------------------------------------------------------
SLIDER_STEPS = 20  # display resolution of the S9 γ slider, which shows no number (ADR 0003); not a model value


def slider_gammas(start: float) -> tuple[list[float | None], int]:
    """The γ at each slider position t ∈ [0, 1]: γ = t/(1 − t), so the ends are ADR 0003's limiting cases, γ = 0 (every
    share counts the same) and γ → ∞ (only the worst-off counts; None in the record). The scenario's starting γ is
    always a position; returns the positions and the index of the start."""
    ts = sorted({k / SLIDER_STEPS for k in range(SLIDER_STEPS + 1)} | {start / (1 + start)})
    gammas: list[float | None] = [None if t == 1 else round6(t / (1 - t)) for t in ts]
    return gammas, ts.index(start / (1 + start))


def debrief_welfare(setup: GameSetup, events: Sequence[Event]) -> dict[str, Any]:
    """S9's welfare slider (ADR 0003): for each season and slider position, the equally-distributed equivalent of PWF_γ
    for every enabled lens's allocation (public, from season.climate) and, only when the table opened per-player
    results, for the water as used (computed on actual use, so it would reveal pumping otherwise; ADR 0004)."""
    opened = next(e["payload"] for e in events if e["type"] == "debrief.opened")
    gammas, start = slider_gammas(setup.scoring.welfareGamma)
    floor = setup.scoring.welfareSupplyFloor

    def row(A: Sequence[float]) -> list[float]:
        return [round6(pwf_ede(A, float("inf") if g is None else g, floor)) for g in gammas]

    climates = {e["season"]: e["payload"] for e in events if e["type"] == "season.climate"}
    # The chosen lens's row uses the allocation issued, which applies the floor rule the table voted (review E1); the
    # season.climate previews use the "whatever works" cut for the sufficientarian lens.
    issued = {e["season"]: e["payload"] for e in events if e["type"] == "allocation.issued"}
    seasons = []
    for e in events:
        if e["type"] != "season.resolved":
            continue
        c = climates[e["season"]]
        demand = [x["demandMm3"] for x in c["schemes"]]
        entry: dict[str, Any] = {
            "season": e["season"],
            "lenses": {p["lens"]: row([q / d for q, d in zip(p["Q"], demand, strict=True)]) for p in c["previews"]},
        }
        chosen = issued.get(e["season"])
        if chosen is not None and chosen["lens"] in entry["lenses"]:
            entry["lenses"][chosen["lens"]] = row([q / d for q, d in zip(chosen["Q"], demand, strict=True)])
        if opened["perPlayer"]:
            entry["used"] = row(e["payload"]["sealed"]["A"])
        seasons.append(entry)
    return {"gammas": gammas, "start": start, "seasons": seasons}


# ---- projections (§6.2: derived, never stored) -------------------------------------------------------------------
def project(events: Sequence[Event], viewer: str) -> list[Event]:
    """The events a viewer may see: 'public' (shared screen, exports before the debrief, relay broadcasts) or a role.
    A role sees public fields plus its own self/sealed entries. Sealed fields open to everyone only when the debrief is
    opened with perPlayer = true; a totals-only debrief opens no per-scheme figure (each of W, A, Y, ΔL, L reveals
    pumping, R17; ADR 0004)."""
    opened = next((e["payload"] for e in events if e["type"] == "debrief.opened"), None)
    out: list[Event] = []
    for e in events:
        vis = e["visibility"]
        if vis == "public":
            out.append(e)
        elif e["type"] == "review.answer":  # S10: written answers stay with their author, whatever the debrief
            if e["actor"] == viewer:
                out.append(e)
        elif vis == "self" or (vis == "sealed" and e["type"] == "action.played"):
            if e["actor"] == viewer or (opened and opened["perPlayer"]):
                out.append(e)
        elif vis == "mixed":
            p = e["payload"]
            mine: dict[str, Any] = {}
            if viewer in p["sealed"]["roles"]:
                i = p["sealed"]["roles"].index(viewer)
                mine = {k: p["sealed"][k][i] for k in ("pumpCost", "P", "W", "A", "Y", "dL", "points", "L", "cropFailure")}
            payload: dict[str, Any]
            if opened and opened["perPlayer"]:
                payload = {"public": p["public"], "sealed": p["sealed"]}
            else:
                # before the debrief, or a totals-only debrief: every per-scheme figure stays sealed, because W, A, Y,
                # ΔL and L each reveal pumping (ADR 0004)
                payload = {"public": p["public"], "self": mine}
            out.append({**e, "payload": payload})
    return out


def audit(setup: GameSetup, events: Sequence[Event]) -> list[str]:
    """ADR 0002: recompute every season from the record with this engine; return any disagreement (empty = verified).
    Also verifies the revealed T and deck against the commitments."""
    problems: list[str] = []
    state = State()
    for e in events:
        resolution = e["type"] in ("season.resolved", "tutorial.resolved")
        if resolution and (state.lens is None or state.climate is None):
            problems.append(f"season {e['season']}: resolved without a chosen lens or an open season")
        elif resolution and state.lens is not None and state.climate is not None:
            played = {
                x["payload"]["role"]: x["payload"]["pumps"]
                for x in events
                if x["type"] == "action.played" and x["season"] == e["season"]
            }
            roles = [s.id for s in setup.schemes]
            lens_params = dict(setup.lenses)[state.lens]
            if state.floorRule:
                lens_params = LensParams(**{**lens_params.__dict__, "floorScaling": state.floorRule})
            schemes = tuple(with_state(x, state.schemes[x.id]) if x.id in state.schemes else x for x in setup.schemes)
            r: dict[str, Any] = dict(
                resolve_season(
                    schemes,
                    tutorial_basin(setup.basin) if e["type"] == "tutorial.resolved" else setup.basin,
                    state.climate["inflow"],
                    state.stock,
                    state.lens,
                    lens_params,
                    [played[x] for x in roles],
                    setup.scoring,
                )
            )
            for k in PUBLIC_RESULT_FIELDS:
                if r[k] != e["payload"]["public"][k]:
                    problems.append(
                        f"season {e['season']}: {k} recomputes to {r[k]}, record has {e['payload']['public'][k]}"
                    )
            for k in SEALED_RESULT_FIELDS:
                if r[k] != e["payload"]["sealed"][k]:
                    problems.append(f"season {e['season']}: sealed {k} differs")
            sealed = e["payload"]["sealed"]
            cost = sealed.get("actionCost", [0.0] * len(roles))
            if sealed["points"] != [round6(d - c) for d, c in zip(r["dL"], cost, strict=True)]:
                problems.append(f"season {e['season']}: sealed points differ from ΔL")
        state = apply_event(state, e)
    recorded_welfare = next((e["payload"] for e in events if e["type"] == "debrief.welfare"), None)
    if recorded_welfare is not None:
        cut = next(i for i, e in enumerate(events) if e["type"] == "debrief.welfare")
        if debrief_welfare(setup, events[:cut]) != recorded_welfare:
            problems.append("debrief.welfare does not recompute from the record")
    created = next((e for e in events if e["type"] == "game.created"), None)
    ended = next((e for e in events if e["type"] == "game.ended"), None)
    if created and ended and not verify_reveal(created, ended):
        problems.append("revealed T or deck does not match the commitments")
    if created and ended:
        recorded = created["payload"].get("runtime", {}).get("numpy")
        if recorded == np.__version__:
            drawn = draw_secrets(setup, ended["payload"]["nonce"])
            if (drawn.T, drawn.deckOrder) != (ended["payload"]["T"], ended["payload"]["deckOrder"]):
                problems.append("the revealed nonce does not reproduce the revealed T and deck")
        else:
            problems.append(
                f"note: recorded under numpy {recorded}, audited under {np.__version__}; the commitments were checked, "
                "but the deck/T draw from the nonce cannot be re-derived across NumPy versions"
            )
    return problems
