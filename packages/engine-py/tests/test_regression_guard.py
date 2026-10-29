# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""ADR 0017 decision 6: while scheme mode is built, the basin game must come out unchanged. Two guards, beside the
conformance vectors of test_vectors_current.py:

- whole Kelvara games, played by the balance harness's strategies, match packages/engine/fixtures/default-basin-guard.json
  (regenerate with scripts/generate_regression_guard.py);
- the client's UI fixtures match what scripts/generate_ui_fixture.py writes now.

Numbers are compared as test_vectors_current.py compares them, so platform last-bit differences cannot flake CI; every
key must match too, so a field added to the output is seen."""

import functools
import json
import sys
from pathlib import Path

import pytest
from blueprint import FIXTURES, ROOT
from test_vectors_current import diffs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_regression_guard as guard
import generate_ui_fixture as ui

UI_NOW = functools.cache(ui.build)  # built once for all its parametrised cases
REGENERATE = "a basin result changed: if that is intended, regenerate the fixture by its script and say why in the PR"


def key_paths(value, path=""):
    """Every key path in a JSON value, so a key added or removed on either side is reported."""
    if isinstance(value, dict):
        return {p for k, v in value.items() for p in {f"{path}.{k}", *key_paths(v, f"{path}.{k}")}}
    if isinstance(value, list):
        return {p for i, v in enumerate(value) for p in key_paths(v, f"{path}[{i}]")}
    return set()


def same(got, want):
    return sorted(key_paths(got) ^ key_paths(want))[:10] + diffs(got, want)[:10]


@pytest.fixture(scope="module")
def guard_now():
    return json.loads(json.dumps(guard.build()))


def test_the_kelvara_guard_games_are_unchanged(guard_now):
    committed = json.loads((FIXTURES / "default-basin-guard.json").read_text(encoding="utf-8"))
    assert same(guard_now, committed) == [], REGENERATE


def test_the_guard_covers_every_enabled_lens_and_a_defecting_seat(guard_now):
    lenses = {lens for lens, _ in guard.balance.setup_with({}).lenses}
    principled = {t[0].split(":", 1)[1] for t in (g["table"] for g in guard_now["games"]) if t[0].startswith("principled:")}
    assert lenses <= principled
    assert any("selfish" in g["table"] for g in guard_now["games"])


@pytest.mark.parametrize("name", sorted(UI_NOW()))
def test_the_ui_fixtures_are_current(name):
    committed = json.loads((ROOT / "packages" / "ui" / "src" / "fixtures" / name).read_text(encoding="utf-8"))
    assert same(json.loads(UI_NOW()[name]), committed) == [], REGENERATE


def test_the_guard_holds_a_game_of_each_length(guard_now):
    """The blueprint's game length is "T ∈ {5, 6}"; the guard plays both."""
    assert {g["T"] for g in guard_now["games"]} == {5, 6}
