# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The committed golden vectors and β set must be what the engine produces now (regenerate with
scripts/generate_vectors.py). Compared numerically, so platform last-bit differences in scipy cannot flake CI."""

import json
import sys
from pathlib import Path

import pytest
from blueprint import FIXTURES

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_vectors import build, jsonable

ROUNDING_STEP, RELATIVE = 1e-6, 1e-9  # tolerance: §7.2 rounding step; relative for large raw sums


def diffs(got, want, path="", out=None):
    out = [] if out is None else out
    if isinstance(want, (int, float)) and not isinstance(want, bool):
        if abs(got - want) > ROUNDING_STEP + RELATIVE * abs(want):
            out.append(f"{path}: now {got} vs committed {want}")
    elif isinstance(want, list):
        if len(got) != len(want):
            out.append(f"{path}: length")
        for i, (g, w) in enumerate(zip(got, want, strict=True)):
            diffs(g, w, f"{path}[{i}]", out)
    elif isinstance(want, dict):
        for k, w in want.items():
            diffs(got.get(k), w, f"{path}.{k}", out)
    elif got != want:
        out.append(f"{path}: now {got!r} vs committed {want!r}")
    return out


@pytest.fixture(scope="module")
def fresh():
    vectors, beta = build()
    return json.loads(json.dumps(vectors, default=jsonable)), json.loads(json.dumps(beta, default=jsonable))


def test_conformance_vectors_are_current(fresh):
    committed = json.loads((FIXTURES / "conformance.json").read_text(encoding="utf-8"))
    assert diffs(fresh[0], committed)[:10] == []


def test_beta_set_is_current(fresh):
    committed = json.loads((FIXTURES / "default-basin-beta.json").read_text(encoding="utf-8"))
    assert diffs(fresh[1], committed)[:10] == []
