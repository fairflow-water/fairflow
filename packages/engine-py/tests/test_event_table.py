# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2: the generated event table (scripts/generate_event_table.py) matches what record.py emits. If an
event, its visibility, its actor or its payload fields change, this fails until the script is run again."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_event_table as gen  # noqa: E402

RECORD = (ROOT / "packages/engine-py/src/fairflow_engine/record.py").read_text(encoding="utf-8")


def test_the_blueprint_carries_the_table_record_py_implies():
    blueprint = (ROOT / "docs/blueprint.md").read_text(encoding="utf-8")
    assert gen.current_block(blueprint) == gen.table(RECORD), "run packages/engine-py/scripts/generate_event_table.py"


def test_every_event_type_emitted_has_a_row():
    emitted = set(re.findall(r'_emit\(\s*"([a-zA-Z]+\.[a-zA-Z]+)"', RECORD))
    rows = set(re.findall(r"^\| `([a-zA-Z]+\.[a-zA-Z]+)` \|", gen.table(RECORD), re.M))
    assert emitted == rows


def test_a_changed_emit_changes_the_table():
    """A drift is seen: a new field, a field made conditional and a new visibility each change the output."""
    base = gen.table(RECORD)
    added = RECORD.replace('{"lens": lens, "voter": actor}', '{"lens": lens, "voter": actor, "weight": 1}')
    optional = RECORD.replace('{"lens": lens}, season=s.season)', '{**({"lens": lens} if lens else {})}, season=s.season)')
    hidden = RECORD.replace('"lens.vetoed", actor, "public"', '"lens.vetoed", actor, "self"')
    for changed, expect in ((added, "weight"), (optional, "lens?"), (hidden, "self")):
        assert changed != RECORD
        out = gen.table(changed)
        assert out != base and expect in out


def test_the_rows_read_as_the_record_does():
    """Spot checks against record.py itself: an optional spread, a field-wide spread and a chosen actor."""
    t = gen.table(RECORD)
    chosen = next(line for line in t.splitlines() if line.startswith("| `lens.chosen`"))
    assert "`veto?`" in chosen and "`revote?`" in chosen and "`lens`" in chosen and "authority" in chosen
    played = next(line for line in t.splitlines() if line.startswith("| `action.played`"))
    assert "`autoCommitted?`" in played and "sealed" in played
