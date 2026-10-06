# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""No number may appear in engine code without saying where it comes from. Model parameters never appear at all (they
come from the scenario or the registry); the only literals allowed are 0, 1 and constants on a line whose comment cites
a blueprint section (§…), an ADR, or marks a numerical tolerance, the §7.2 rounding or an array layout."""

import ast
import re

from blueprint import ROOT

MARK = re.compile(r"(#|//).*(§\d|ADR \d|tolerance|rounding|layout)")


def py_literals():
    for f in sorted((ROOT / "packages" / "engine-py" / "src" / "fairflow_engine").glob("*.py")):
        lines = f.read_text(encoding="utf-8").splitlines()
        for node in ast.walk(ast.parse("\n".join(lines))):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float) and node.value not in (0, 1):
                yield f.name, node.lineno, node.value, lines[node.lineno - 1]


def ts_literals():
    """Numeric literals in the TypeScript mirror's source, outside comments and strings (a lexer is enough here)."""
    token = re.compile(
        r"//[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`|(?<![\w.])(\d+(?:\.\d+)?(?:e-?\d+)?)(?![\w.])",
        re.S,
    )
    for f in sorted((ROOT / "packages" / "engine" / "src").glob("*.ts")):
        if f.name.endswith((".test.ts", ".testutil.ts")):
            continue
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        for m in token.finditer(text):
            if m.group(1) and float(m.group(1)) not in (0, 1):
                n = text.count("\n", 0, m.start()) + 1
                yield f.name, n, m.group(1), lines[n - 1]


def unsourced(literals):
    return [f"{name}:{line}: {value} — {text.strip()}" for name, line, value, text in literals if not MARK.search(text)]


def test_python_engine_has_no_unsourced_numbers():
    assert unsourced(py_literals()) == []


def test_typescript_mirror_has_no_unsourced_numbers():
    assert unsourced(ts_literals()) == []


def test_the_check_catches_a_bare_parameter():
    assert unsourced([("x.py", 1, 0.5, "floor = 0.5")]) and not unsourced([("x.py", 1, 2, "h = d / 2  # §2.3 half-claims")])
