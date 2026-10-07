# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Write the client's test fixtures from the real engine: the opening of a game on the shipped default scenario, as the
projector ("public") and as player A receive it. The client's tests then render engine output, never hand-made numbers.

Run: python scripts/generate_ui_fixture.py   (from packages/engine-py)
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
import blueprint as bp  # noqa: E402

from fairflow_engine import AUTHORITY, Game, project  # noqa: E402
from fairflow_engine.scenario import load_scenario  # noqa: E402

OUT = bp.ROOT / "packages" / "ui" / "src" / "fixtures"
NONCE = "f" * 32  # fixture input: a fixed nonce so the file is reproducible


def main() -> None:
    scenario = json.loads((bp.ROOT / "packages" / "scenarios" / "default-basin.json").read_text(encoding="utf-8"))
    setup = load_scenario(scenario, bp.registry()).setup
    assert setup is not None
    tick = iter(range(10**6))
    g = Game.create(setup, "FIXTR", "room", {"appVersion": "fixture"}, lambda: f"2026-10-07T09:00:{next(tick):02d}Z", NONCE)
    for role in [*(s.id for s in setup.schemes), AUTHORITY]:
        g.submit(role, "join", deviceHash=f"fixture-{role}", consentGiven=True, presurveyComplete=True)
    g.submit(AUTHORITY, "start_season")
    g.submit(AUTHORITY, "propose", lens="proportional")
    g.submit(AUTHORITY, "propose", lens="utilitarian")
    g.submit("A", "vote", lens="utilitarian")
    g.submit("B", "vote", lens="proportional")
    g.submit("C", "vote", lens="proportional")
    g.submit(AUTHORITY, "close_vote")
    opening = list(g.events)
    # then play to the end: A pumps, B expands once, so S6-S8 have real private turns, results and goals
    first = True
    while True:
        for i, s in enumerate(setup.schemes):
            g.submit(s.id, "commit", pumps=1.0 if i == 0 else 0.0, action="expand" if (i == 1 and first) else None)
        first = False
        if g.events[-1]["type"] == "goal.result" or any(e["type"] == "game.ended" for e in g.events):
            break
        g.submit(AUTHORITY, "start_season")
        g.submit(AUTHORITY, "propose", lens="proportional")
        for s in setup.schemes:
            g.submit(s.id, "vote", lens="proportional")
        g.submit(AUTHORITY, "close_vote")
    public_scenario = {
        "name": scenario["name"],
        "schemes": [{k: s[k] for k in ("id", "name", "seat", "shape", "glyph", "crop")} for s in scenario["schemes"]],
        "lenses": [
            {"id": lens["id"], "plainName": lens.get("plainName", lens["id"])}
            for lens in scenario["lenses"]
            if lens["enabled"]
        ],
        "session": scenario["session"],
    }
    # S9/S10: the same game after each debrief choice; player A saves one review answer after the per-player debrief
    totals = copy.deepcopy(g)
    totals.submit(AUTHORITY, "open_debrief", perPlayer=False)
    g.submit(AUTHORITY, "open_debrief", perPlayer=True)
    g.submit("A", "review_answer", part=1, item="like.1", value="fixture answer")
    OUT.mkdir(parents=True, exist_ok=True)
    played = g.events[: len(totals.events) - 2]  # the game as it ended, before debrief.opened and debrief.welfare
    stages = (("opening", opening), ("game", played), ("debrief", g.events), ("totals", totals.events))
    for stage, events in stages:
        for name, viewer in (("public", "public"), ("A", "A")):
            data = {
                "generatedBy": "packages/engine-py/scripts/generate_ui_fixture.py",
                "scenario": public_scenario,
                "events": project(events, viewer),
            }
            text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
            (OUT / f"{stage}-{name}.json").write_text(text, encoding="utf-8", newline="\n")  # LF on every platform
    print(f"wrote {', '.join(f'{n}-*' for n, _ in stages)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
