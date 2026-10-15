# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2: the generated event table (scripts/generate_event_table.py) matches what record.py emits. If an
event, its visibility, its permitted role or its payload fields change, this fails until the script is run again. The
hand-written "Not yet emitted" list stays apart from it: an event leaves the list when record.py first emits it."""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_event_table as gen  # noqa: E402

RECORD = (ROOT / "packages/engine-py/src/fairflow_engine/record.py").read_text(encoding="utf-8")
BLUEPRINT = (ROOT / "docs/blueprint.md").read_text(encoding="utf-8")


def row(kind: str) -> str:
    return next(line for line in gen.table(RECORD).splitlines() if line.startswith(f"| `{kind}` |"))


def test_the_blueprint_carries_the_table_record_py_implies():
    assert gen.current_block(BLUEPRINT) == gen.table(RECORD), "run packages/engine-py/scripts/generate_event_table.py"


def test_every_event_type_emitted_has_a_row():
    emitted = set(re.findall(r'_emit\(\s*"([a-zA-Z]+\.[a-zA-Z]+)"', RECORD))
    rows = set(re.findall(r"^\| `([a-zA-Z]+\.[a-zA-Z]+)` \|", gen.table(RECORD), re.M))
    assert emitted == rows


def test_the_not_yet_emitted_list_holds_only_events_the_engine_does_not_write():
    planned = gen.planned(BLUEPRINT)
    assert planned, "the §6.2 'Not yet emitted' list is missing"
    assert not set(planned) & set(gen.emitted(RECORD)), "an emitted event is still listed as not yet emitted"
    assert len(planned) == len(set(planned))


def test_every_role_note_still_matches_an_emitting_site():
    """A note for an (event, actor expression) that record.py no longer has would silently stop applying."""
    sites = set()
    for call in ast.walk(ast.parse(RECORD)):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "_emit":
            kind = call.args[0]
            if isinstance(kind, ast.Constant):
                sites.add((kind.value, ast.unparse(call.args[1])))
    assert set(gen.ROLE_NOTES) <= sites


def test_a_changed_emit_changes_the_table():
    """A drift is seen: a new field, a field made conditional, a new visibility and a new role check each change it."""
    base = gen.table(RECORD)
    added = RECORD.replace('{"lens": lens, "voter": actor}', '{"lens": lens, "voter": actor, "weight": 1}')
    optional = RECORD.replace('{"lens": lens}, season=s.season)', '{**({"lens": lens} if lens else {})}, season=s.season)')
    hidden = RECORD.replace('"lens.vetoed", actor, "public"', '"lens.vetoed", actor, "self"')
    checked = RECORD.replace(
        "    def _on_propose(self, s: State, actor: str, lens: str) -> None:\n",
        "    def _on_propose(self, s: State, actor: str, lens: str) -> None:\n"
        '        self._need(actor == AUTHORITY, "not_authority", "")\n',
    )
    for changed, expect in (
        (added, "weight"),
        (optional, "lens?"),
        (hidden, "self"),
        (checked, "| `lens.proposed` | authority"),
    ):
        assert changed != RECORD
        out = gen.table(changed)
        assert out != base and expect in out


def test_the_rows_read_as_the_record_does():
    """Spot checks against record.py itself: permitted roles from the handlers' checks, optional spreads, and keys one
    level down (a literal, a comprehension over a module tuple, and keys added afterwards)."""
    assert "| `lens.vetoed` | authority |" in row("lens.vetoed")
    assert "| `lens.voted` | irrigation scheme |" in row("lens.voted")
    assert "authority or engine" in row("lens.chosen") and "`veto?`" in row("lens.chosen")
    assert "`autoCommitted?`" in row("action.played") and "sealed" in row("action.played")
    assert "`commitments` (`gameLength`, `deckOrder`)" in row("game.created")
    resolved = row("season.resolved")
    assert "`public` (`allocable`" in resolved and "`bands`" in resolved and "`pumpsBy`" in resolved
    assert "`bands`" not in row("tutorial.resolved")  # the practice round's public part has no band words
