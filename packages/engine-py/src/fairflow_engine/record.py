# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Blueprint §6.2 — the Season Record: an append-only event log with a visibility class per event (or per field),
driven by intents that the engine validates (R1–R20, without modules M2–M6 yet).

Clients submit intents; the engine either rejects one (typed `Rejection`, state unchanged) or appends events. Every
number in an event is computed here by the engine, never by a client. The game length T and the deck order are drawn
from a secret nonce, committed by SHA-256 at creation and revealed at `game.ended` (§4.1 R4, §7.2)."""

from __future__ import annotations

import copy
import hashlib
import secrets as _secrets
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional, Sequence

import numpy as np

from .allocate import FLOOR_RULES
from .model import Basin, LensId, LensParams, Scheme, Scoring
from .season import resolve_season, verdict

Visibility = Literal["public", "self", "sealed", "mixed"]
AUTHORITY = "authority"
WHATEVER_WORKS = "whatever_works"  # ADR 0003: the "whatever works" option

# §6.2 as amended by ADR 0004: during play only these are public; every figure computed on actual use is sealed
# until the debrief (each one, with the public allocation, lets the table solve for individual pumping).
PUBLIC_RESULT_FIELDS = ("allocable", "pumpsTotal", "observedStockNext", "inflowLossNext", "asAllocated",
                        "sustainabilityBand")
SEALED_RESULT_FIELDS = ("pumpCost", "P", "W", "A", "Y", "dL", "stockNext", "returnFlow", "ePJ", "eSE", "gini",
                        "giniCorrected", "F", "S", "triangle", "welfare")


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
    inflow: dict[str, float]            # absolute inflow per card (§2.2)
    deck: dict[str, int]                # cards per type, e.g. from scenario basin.deck
    gameLength: tuple[int, int]         # (min, max), T ~ Uniform{min..max}
    scoring: Scoring
    lenses: tuple[tuple[LensId, LensParams], ...]   # enabled lenses in card order
    defaultLens: LensId
    floorRules: tuple[str, ...]         # ADR 0003 options offered (keys of FLOOR_RULES)


@dataclass
class Secrets:
    """Held by the engine host only (the relay in room mode, the device in table mode); revealed at game.ended."""
    nonce: str
    T: int
    deckOrder: list[str]


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


def verify_reveal(created: dict, ended: dict) -> bool:
    """Anyone can check the revealed T and deck against the commitments made at creation."""
    c, e = created["payload"]["commitments"], ended["payload"]
    return (commitment(e["nonce"], str(e["T"])) == c["gameLength"]
            and commitment(e["nonce"], ",".join(e["deckOrder"])) == c["deckOrder"])


@dataclass
class State:
    """What the events imply. Rebuilt by replaying the record (`replay`); never stored."""
    phase: str = "lobby"     # lobby → vote → [tiebreak] → [floor_vote] → private → reveal → … → ended
    season: int = 0
    stock: float = 0.0
    inflowLoss: float = 0.0
    players: dict[str, dict] = field(default_factory=dict)
    proposals: list[str] = field(default_factory=list)
    votes: dict[str, str] = field(default_factory=dict)
    floorVotes: dict[str, str] = field(default_factory=dict)
    lens: Optional[str] = None
    previousLens: Optional[str] = None
    floorRule: Optional[str] = None
    allocation: Optional[dict] = None
    climate: Optional[dict] = None
    committed: set[str] = field(default_factory=set)
    livelihood: dict[str, float] = field(default_factory=dict)
    lowRun: dict[str, int] = field(default_factory=dict)       # consecutive seasons at A ≤ survival floor
    cropFailure: dict[str, bool] = field(default_factory=dict)
    scores: list[float] = field(default_factory=list)
    timeboxed: bool = False
    debrief: Optional[dict] = None


def apply_event(state: State, event: dict) -> State:
    """Pure fold step: state after `event`. Numbers are taken from the event, never recomputed here."""
    s = copy.deepcopy(state)
    p, kind = event["payload"], event["type"]
    if kind == "game.created":
        s.stock = p["aquiferInitial"]
        s.livelihood = {r: 0.0 for r in p["schemeRoles"]}
        s.lowRun = {r: 0 for r in p["schemeRoles"]}
        s.cropFailure = {r: False for r in p["schemeRoles"]}
    elif kind == "player.joined":
        s.players[p["role"]] = p
    elif kind == "season.climate":
        s.season, s.climate, s.phase = event["season"], p, "vote"
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
    elif kind == "season.resolved":
        pub, sealed = p["public"], p["sealed"]
        s.stock, s.inflowLoss, s.phase = sealed["stockNext"], pub["inflowLossNext"], "reveal"
        s.scores.append(sealed["triangle"]["score"])
        for role, L, run, failed in zip(sealed["roles"], sealed["L"], sealed["lowRun"], sealed["cropFailure"]):
            s.livelihood[role], s.lowRun[role], s.cropFailure[role] = L, run, failed
    elif kind == "game.timeboxed":
        s.timeboxed = True
    elif kind == "game.ended":
        s.phase = "ended"
    elif kind == "debrief.opened":
        s.debrief = p
    return s


def replay(events: Sequence[dict]) -> State:
    """state = events.reduce(applyEvent, initialState) (§6.2)."""
    state = State()
    for e in events:
        state = apply_event(state, e)
    return state


class Game:
    """The engine host's view of one game: the record plus the secrets. `submit` is the only way in."""

    def __init__(self, setup: GameSetup, secrets: Secrets, events: list[dict], clock: Callable[[], str]):
        self.setup, self.secrets, self.events, self.clock = setup, secrets, events, clock

    # ---- creation ------------------------------------------------------------------------------------------------
    @classmethod
    def create(cls, setup: GameSetup, game_id: str, mode: str, versions: dict, clock: Callable[[], str],
               nonce: Optional[str] = None) -> "Game":
        nonce = nonce or _secrets.token_hex(16)  # layout: 128-bit secret nonce
        sec = draw_secrets(setup, nonce)
        game = cls(setup, sec, [], clock)
        game._emit("game.created", "engine", "public", {
            "gameId": game_id, "mode": mode, **versions,
            "schemeRoles": [s.id for s in setup.schemes], "aquiferInitial": setup.basin.aquifer.initial,
            "commitments": {"gameLength": commitment(nonce, str(sec.T)), "deckOrder": commitment(nonce, ",".join(sec.deckOrder))},
            "lenses": [lens for lens, _ in setup.lenses], "defaultLens": setup.defaultLens,
            "floorRules": list(setup.floorRules),
        })
        return game

    @property
    def state(self) -> State:
        return replay(self.events)

    # ---- intents -------------------------------------------------------------------------------------------------
    def submit(self, actor: str, intent: str, **args) -> list[dict]:
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

    def _on_join(self, s: State, actor: str, deviceHash: str, consentGiven: bool, presurveyComplete: bool) -> None:
        """R2, R3: a role is taken once; consent and pre-survey are recorded before the role is shown."""
        self._need(s.phase == "lobby", "wrong_phase", "players join before season 1")
        self._need(actor in self._scheme_roles() + [AUTHORITY], "unknown_role", actor)
        self._need(actor not in s.players, "role_taken", actor)
        self._emit("player.joined", actor, "public", {"role": actor, "deviceId": deviceHash,
                                                       "consentGiven": consentGiven, "presurveyComplete": presurveyComplete})

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
        self._emit("season.climate", "engine", "public",
                   {"card": card, "inflow": inflow, "reserve": self.setup.basin.reserve,
                    "allocable": max(0.0, inflow - self.setup.basin.reserve)}, season=season)

    def _on_propose(self, s: State, actor: str, lens: str) -> None:
        """R7: lenses are proposed aloud; the record keeps lens and proposer."""
        self._need(s.phase == "vote", "wrong_phase", s.phase)
        self._need(lens in [l for l, _ in self.setup.lenses], "lens_not_enabled", lens)
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
            self._choose(s, s.proposals[0], tally={}, by_timeout=False)
            return
        top = max(tally.values())
        leaders = sorted(l for l, n in tally.items() if n == top)
        if len(leaders) > 1:
            self._emit("lens.tied", "engine", "public", {"leaders": leaders, "tally": dict(tally)}, season=s.season)
            return
        self._choose(s, leaders[0], tally=dict(tally), by_timeout=False)

    def _on_break_tie(self, s: State, actor: str, lens: str) -> None:
        self._need(actor == AUTHORITY, "not_authority", "only the Authority breaks a tie")
        self._need(s.phase == "tiebreak", "wrong_phase", s.phase)
        tied = next(e for e in reversed(self.events) if e["type"] == "lens.tied")["payload"]
        self._need(lens in tied["leaders"], "not_a_leader", lens)
        self._choose(s, lens, tally=tied["tally"], by_timeout=False, tie_break=True)

    def _choose(self, s: State, lens: str, tally: dict, by_timeout: bool, tie_break: bool = False) -> None:
        floors_short = lens == "sufficientarian" and self._floors_exceed(s)
        self._emit("lens.chosen", AUTHORITY if tie_break else "engine", "public",
                   {"lens": lens, "tally": tally, "byTimeout": by_timeout, "tieBreak": tie_break,
                    "floorVoteNeeded": floors_short}, season=s.season)
        if not floors_short:
            self._issue_allocation(lens, None, s)

    def _floors_exceed(self, s: State) -> bool:
        params = dict(self.setup.lenses)["sufficientarian"]
        floor = params.need("floor", "sufficientarian")
        return sum(floor * x.demandMm3 for x in self.setup.schemes) >= s.climate["allocable"]

    def _on_floor_vote(self, s: State, actor: str, rule: str) -> None:
        """ADR 0003: when the sufficientarian floors exceed the water, the table votes how to cut them."""
        self._need(s.phase == "floor_vote", "wrong_phase", s.phase)
        self._need(actor in self._scheme_roles(), "not_a_voter", actor)
        self._need(rule in self.setup.floorRules or rule == WHATEVER_WORKS, "rule_not_offered", rule)
        self._emit("lens.floorVoted", actor, "public", {"rule": rule, "voter": actor}, season=s.season)

    def _on_close_floor_vote(self, s: State, actor: str, tieBreak: Optional[str] = None) -> None:
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
                self._need(tieBreak in leaders, "tie", f"Authority must break the tie among {leaders}")
                rule = tieBreak
            else:
                rule = leaders[0]
            by_timeout = False
        applied = "proportional" if rule == WHATEVER_WORKS else rule
        self._emit("lens.floorRule", "engine", "public",
                   {"rule": rule, "applied": applied, "tally": dict(tally), "byTimeout": by_timeout}, season=s.season)
        self._issue_allocation("sufficientarian", applied, s)

    def _lens_params(self, lens: str, floor_rule: Optional[str]) -> LensParams:
        params = dict(self.setup.lenses)[lens]
        if floor_rule is None:
            return params
        return LensParams(**{**params.__dict__, "floorScaling": floor_rule})

    def _issue_allocation(self, lens: str, floor_rule: Optional[str], s: State) -> None:
        """R9: the engine computes Q under the lens; surplus to the aquifer. Public."""
        r = self._resolve(s, lens, floor_rule, pumps=[0.0] * len(self.setup.schemes))
        self._emit("allocation.issued", "engine", "public",
                   {"lens": lens, "floorRule": floor_rule, "Q": r["allocation"]["Q"],
                    "surplusToAquifer": r["allocation"]["surplusToAquifer"]}, season=s.season)

    def _on_commit(self, s: State, actor: str, pumps: float) -> None:
        """R10: each scheme commits its private turn (0..cap pumps). Sealed until the debrief."""
        self._need(s.phase == "private", "wrong_phase", s.phase)
        self._need(actor in self._scheme_roles(), "not_a_scheme", actor)
        self._need(actor not in s.committed, "already_committed", actor)
        self._need(0 <= pumps <= self.setup.basin.pump.cap, "pump_out_of_range", f"0..{self.setup.basin.pump.cap}")
        self._emit("action.played", actor, "sealed", {"role": actor, "pumps": pumps, "committedAt": self.clock()},
                   season=s.season)
        if s.committed | {actor} == set(self._scheme_roles()):
            self._resolve_season(replay(self.events))

    def _resolve(self, s: State, lens: str, floor_rule: Optional[str], pumps: list[float]) -> dict:
        return resolve_season(self.setup.schemes, self.setup.basin, s.climate["inflow"], s.stock, lens,
                              self._lens_params(lens, floor_rule), pumps, self.setup.scoring)

    def _resolve_season(self, s: State) -> None:
        """R11: pumps drawn, rationed; W, Y, ΔL, dials; aquifer stepped. Mixed visibility (§6.2)."""
        roles = self._scheme_roles()
        played = {e["payload"]["role"]: e["payload"]["pumps"] for e in self.events
                  if e["type"] == "action.played" and e["season"] == s.season}
        pumps = [played[r] for r in roles]
        r = self._resolve(s, s.lens, s.floorRule, pumps)
        floor = self.setup.scoring.survivalFloor
        low_run = [s.lowRun[role] + 1 if a <= floor else 0 for role, a in zip(roles, r["A"])]
        failed = [s.cropFailure[role] or run >= 2 for role, run in zip(roles, low_run)]  # §2.4: two consecutive seasons
        L = [s.livelihood[role] + d for role, d in zip(roles, r["dL"])]
        v = verdict(self.setup.schemes, r["allocable"], r["W"], s.lens, r["pumpsTotal"], self.setup.lenses, floor)
        public = {k: r[k] for k in PUBLIC_RESULT_FIELDS}
        sealed = {k: r[k] for k in SEALED_RESULT_FIELDS}
        sealed.update({"roles": roles, "pumpsBy": dict(zip(roles, r["P"])), "L": L, "lowRun": low_run,
                       "cropFailure": failed, "cropFailureFlag": any(failed),
                       "verdict": {k: v[k] for k in ("voted", "satisfied", "pumpingGap")}})
        self._emit("season.resolved", "engine", "mixed", {"public": public, "sealed": sealed}, season=s.season)
        after = replay(self.events)
        if after.season >= self.secrets.T or after.timeboxed:
            self._end(after)

    def _on_timebox(self, s: State, actor: str, sessionMinute: float) -> None:
        """R20: the facilitator time-box ends play after the current season; T is still revealed."""
        self._need(actor == AUTHORITY, "not_authority", "only the facilitator time-boxes")
        self._need(s.phase not in ("ended",) and not s.timeboxed, "wrong_phase", s.phase)
        self._emit("game.timeboxed", actor, "public", {"atSeason": s.season, "sessionMinute": sessionMinute}, season=s.season)
        if s.phase in ("lobby", "reveal"):
            self._end(replay(self.events))

    def _end(self, s: State) -> None:
        sec = self.secrets
        self._emit("game.ended", "engine", "public", {
            "T": sec.T, "nonce": sec.nonce, "deckOrder": sec.deckOrder, "truncated": s.timeboxed or s.season < sec.T,
            "seasonsPlayed": s.season, "collectiveScore": float(np.mean(s.scores)) if s.scores else 0.0,
            "cropFailureFlag": any(s.cropFailure.values())}, season=s.season)

    def _on_open_debrief(self, s: State, actor: str, perPlayer: bool) -> None:
        """R19: sealed fields become readable; perPlayer = false keeps pumpsBy sealed in every projection."""
        self._need(actor == AUTHORITY, "not_authority", "only the facilitator opens the debrief")
        self._need(s.phase == "ended" and s.debrief is None, "wrong_phase", s.phase)
        self._emit("debrief.opened", actor, "public", {"perPlayer": perPlayer}, season=s.season)

    # ---- record --------------------------------------------------------------------------------------------------
    def _emit(self, kind: str, actor: str, visibility: Visibility, payload: dict, season: Optional[int] = None) -> None:
        self.events.append({"seq": len(self.events) + 1, "t": self.clock(), "season": season if season is not None else 0,
                            "actor": actor, "type": kind, "payload": payload, "visibility": visibility})


# ---- projections (§6.2: derived, never stored) -------------------------------------------------------------------
def project(events: Sequence[dict], viewer: str) -> list[dict]:
    """The events a viewer may see: 'public' (shared screen, exports before the debrief, relay broadcasts) or a role.
    A role sees public fields plus its own self/sealed entries. After debrief.opened, sealed fields are public; with
    perPlayer = false no per-scheme figure is opened (each of W, A, Y, ΔL, L reveals pumping, R17)."""
    opened = next((e["payload"] for e in events if e["type"] == "debrief.opened"), None)
    out = []
    for e in events:
        vis = e["visibility"]
        if vis == "public":
            out.append(e)
        elif vis in ("self", "sealed") and e["type"] == "action.played":
            if e["actor"] == viewer or (opened and opened["perPlayer"]):
                out.append(e)
        elif vis == "mixed":
            p = e["payload"]
            mine = {}
            if viewer in p["sealed"]["roles"]:
                i = p["sealed"]["roles"].index(viewer)
                mine = {k: p["sealed"][k][i] for k in ("pumpCost", "P", "W", "A", "Y", "dL", "L", "cropFailure")}
            if opened and opened["perPlayer"]:
                payload = {"public": p["public"], "sealed": p["sealed"]}
            elif opened:
                # perPlayer false: every per-scheme figure stays sealed, because W, A, Y, ΔL and L each reveal pumping
                payload = {"public": p["public"], "self": mine}
            else:
                payload = {"public": p["public"], "self": mine}
            out.append({**e, "payload": payload})
    return out


def audit(setup: GameSetup, events: Sequence[dict]) -> list[str]:
    """ADR 0002: recompute every season from the record with this engine; return any disagreement (empty = verified).
    Also verifies the revealed T and deck against the commitments."""
    problems = []
    state = State()
    for e in events:
        if e["type"] == "season.resolved":
            played = {x["payload"]["role"]: x["payload"]["pumps"] for x in events
                      if x["type"] == "action.played" and x["season"] == e["season"]}
            roles = [s.id for s in setup.schemes]
            lens_params = dict(setup.lenses)[state.lens]
            if state.floorRule:
                lens_params = LensParams(**{**lens_params.__dict__, "floorScaling": state.floorRule})
            r = resolve_season(setup.schemes, setup.basin, state.climate["inflow"], state.stock, state.lens, lens_params,
                               [played[x] for x in roles], setup.scoring)
            for k in PUBLIC_RESULT_FIELDS:
                if r[k] != e["payload"]["public"][k]:
                    problems.append(f"season {e['season']}: {k} recomputes to {r[k]}, record has {e['payload']['public'][k]}")
            for k in SEALED_RESULT_FIELDS:
                if r[k] != e["payload"]["sealed"][k]:
                    problems.append(f"season {e['season']}: sealed {k} differs")
        state = apply_event(state, e)
    created = next((e for e in events if e["type"] == "game.created"), None)
    ended = next((e for e in events if e["type"] == "game.ended"), None)
    if created and ended and not verify_reveal(created, ended):
        problems.append("revealed T or deck does not match the commitments")
    return problems
