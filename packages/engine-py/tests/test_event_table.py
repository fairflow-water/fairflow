# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2: the generated event table (scripts/generate_event_table.py) matches what record.py emits. If an
event, its visibility, its permitted role or its payload fields change, this fails until the script is run again. The
hand-written "Not yet emitted" list stays apart from it: an event leaves the list when record.py first emits it."""

import re
import sys
from pathlib import Path

import pytest

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


def test_every_cause_note_still_names_an_emitted_event():
    """A note for an event record.py no longer emits would silently stop applying."""
    assert set(gen.CAUSE_NOTES) <= set(gen.emitted(RECORD))


def test_an_unrecognised_role_check_stops_the_script():
    """A new form of check on `actor` must be added to NEEDS, not be reported as 'no actor check'."""
    changed = RECORD.replace(
        "    def _on_propose(self, s: State, actor: str, lens: str) -> None:\n",
        '    def _on_propose(self, s: State, actor: str, lens: str) -> None:\n        self._need(actor != "A", "x", "")\n',
    )
    assert changed != RECORD
    with pytest.raises(SystemExit):
        gen.table(changed)


def test_a_changed_emit_changes_the_table():
    """A drift is seen: a new field, a field made conditional, a new visibility and a removed role check each change it."""
    base = gen.table(RECORD)
    added = RECORD.replace('{"lens": lens, "voter": actor}', '{"lens": lens, "voter": actor, "weight": 1}')
    optional = RECORD.replace('{"lens": lens}, season=s.season)', '{**({"lens": lens} if lens else {})}, season=s.season)')
    hidden = RECORD.replace('"lens.vetoed", actor, "public"', '"lens.vetoed", actor, "self"')
    unchecked = RECORD.replace(
        '        self._need(actor == AUTHORITY, "not_authority", "only the Authority taps a proposed lens")\n', ""
    )
    for changed, expect in (
        (added, "weight"),
        (optional, "lens?"),
        (hidden, "self"),
        (unchecked, "| `lens.proposed` | any seated role (no `actor` check) (`propose`)"),
    ):
        assert changed != RECORD
        out = gen.table(changed)
        assert out != base and expect in out


def test_the_rows_read_as_the_record_does():
    """Spot checks against record.py itself: who causes an event (followed through the calls from each intent),
    the recorded actor, optional spreads, and keys one level down (a literal, a comprehension over a module tuple,
    and keys added afterwards)."""
    assert row("lens.vetoed").startswith("| `lens.vetoed` | authority (`veto`) | the sender |")
    assert row("lens.voted").startswith("| `lens.voted` | irrigation scheme (`vote`) |")
    chosen = row("lens.chosen")
    assert "authority (`close_vote`)" in chosen and "the server's timer (`timeout_vote`)" in chosen
    assert "authority (`break_tie`)" in chosen and "authority or engine" in chosen and "`veto?`" in chosen
    assert row("season.climate").startswith(
        "| `season.climate` | authority (`start_tutorial`); authority (`start_season`) | engine |"
    )
    assert "authority (`timebox`)" in row("game.ended")
    assert "`autoCommitted?`" in row("action.played") and "the server's timer (`timeout_private`)" in row("action.played")
    assert "`commitments` (`gameLength`, `deckOrder`)" in row("game.created") and "game creation" in row("game.created")
    resolved = row("season.resolved")
    assert "`public` (`allocable`" in resolved and "`bands`" in resolved and "`pumpsBy`" in resolved
    assert "`bands`" not in row("tutorial.resolved")  # the practice round's public part has no band words
