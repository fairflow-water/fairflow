# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Write the client's test fixtures from the real engine: the opening of a game on the shipped default scenario, as the
projector ("public") and as player A receive it. The client's tests then render engine output, never hand-made numbers.

Run: python scripts/generate_ui_fixture.py   (from packages/engine-py)
"""

from __future__ import annotations

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
    public_scenario = {
        "name": scenario["name"],
        "schemes": [{k: s[k] for k in ("id", "name", "seat", "shape", "glyph", "crop")} for s in scenario["schemes"]],
        "lenses": [
            {"id": lens["id"], "plainName": lens.get("plainName", lens["id"])}
            for lens in scenario["lenses"]
            if lens["enabled"]
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, viewer in (("public", "public"), ("A", "A")):
        data = {
            "generatedBy": "packages/engine-py/scripts/generate_ui_fixture.py",
            "scenario": public_scenario,
            "events": project(g.events, viewer),
        }
        text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
        (OUT / f"opening-{name}.json").write_text(text, encoding="utf-8", newline="\n")  # LF on every platform
    print(f"wrote {OUT}/opening-public.json and opening-A.json ({len(g.events)} events)")


if __name__ == "__main__":
    main()
