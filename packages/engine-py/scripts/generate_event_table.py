# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2: write the table of the events record.py emits into docs/blueprint.md, between the generated-table
markers, by reading the `_emit` calls (type, actor, visibility, payload fields). `--check` exits 1 when the blueprint
is out of date. tests/test_event_table.py runs the same comparison in CI.

A field marked `?` is present only sometimes (a conditional spread, or absent at another emitting site). A payload
built elsewhere is named by the expression that builds it."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / "packages/engine-py/src/fairflow_engine/record.py"
BLUEPRINT = ROOT / "docs/blueprint.md"
BEGIN = "<!-- BEGIN generated event table: packages/engine-py/scripts/generate_event_table.py; do not edit by hand -->"
END = "<!-- END generated event table -->"
ANCHOR = r"**\[Incomplete; `packages/engine-py/src/fairflow_engine/record.py` is the source of truth (handoff §5).\]**"


@dataclass
class Row:
    actors: list[str] = field(default_factory=list)
    visibility: list[str] = field(default_factory=list)
    fields: list[list[tuple[str, bool]]] = field(default_factory=list)  # per emitting site: (name, always present)


def _actor(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name) and node.id == "AUTHORITY":
        return ["authority"]
    if isinstance(node, ast.IfExp):
        return _actor(node.body) + _actor(node.orelse)
    return ["the acting role"]


def _assigned(func: ast.AST, name: str) -> ast.expr | None:
    for n in ast.walk(func):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return n.value
    return None


def _fields(node: ast.expr | None, func: ast.AST, always: bool = True) -> list[tuple[str, bool]] | None:
    """Top-level payload keys with whether each is always present; None when the payload is not a dict literal."""
    if isinstance(node, ast.IfExp):
        one, two = _fields(node.body, func, False), _fields(node.orelse, func, False)
        return None if one is None or two is None else one + two
    if isinstance(node, ast.Name):
        return _fields(_assigned(func, node.id), func, always)
    if not isinstance(node, ast.Dict):
        return None
    out: list[tuple[str, bool]] = []
    for k, v in zip(node.keys, node.values, strict=True):
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out.append((k.value, always))
        elif k is None:  # **spread
            inner = _fields(v, func, always)
            out += inner if inner is not None else [(f"…{ast.unparse(v)}", always)]
    return out


def _rows(source: str) -> dict[str, Row]:
    tree = ast.parse(source)
    rows: dict[str, Row] = {}
    funcs = [f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)]
    for func in funcs:
        for call in ast.walk(func):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "_emit"):
                continue
            kind = call.args[0]
            if not (isinstance(kind, ast.Constant) and isinstance(kind.value, str)):
                continue
            row = rows.setdefault(kind.value, Row())
            for a in _actor(call.args[1]):
                if a not in row.actors:
                    row.actors.append(a)
            vis = call.args[2]
            v = vis.value if isinstance(vis, ast.Constant) else ast.unparse(vis)
            if v not in row.visibility:
                row.visibility.append(v)
            payload = _fields(call.args[3], func)
            row.fields.append(payload if payload is not None else [(f"(built by `{ast.unparse(call.args[3])}`)", True)])
    return rows


def _payload(sites: list[list[tuple[str, bool]]]) -> str:
    names: list[str] = []
    for site in sites:
        for name, _ in site:
            if name not in names:
                names.append(name)
    out = []
    for name in names:
        always = all(any(n == name and a for n, a in site) for site in sites)
        out.append(name if name.startswith("(") else f"`{name}{'' if always else '?'}`")
    return ", ".join(out)


def table(source: str) -> str:
    """The generated markdown table for a record.py source text, in the order record.py first emits each type."""
    lines = ["| Event | Actor | Visibility | Payload fields |", "|---|---|---|---|"]
    for kind, row in _rows(source).items():
        lines.append(f"| `{kind}` | {' or '.join(row.actors)} | {' or '.join(row.visibility)} | {_payload(row.fields)} |")
    return "\n".join(lines)


def current_block(blueprint: str) -> str | None:
    if BEGIN not in blueprint:
        return None
    return blueprint.split(BEGIN, 1)[1].split(END, 1)[0].strip()


def render(blueprint: str, source: str) -> str:
    block = f"{BEGIN}\n{table(source)}\n{END}"
    if BEGIN in blueprint:
        head, rest = blueprint.split(BEGIN, 1)
        return head + block + rest.split(END, 1)[1]
    i = blueprint.index(ANCHOR)
    end = blueprint.index("\n\n", i)
    intro = "\n\nWhat `record.py` emits today, generated from its `_emit` calls (`?`: not always present):\n\n"
    return blueprint[:end] + intro + block + blueprint[end:]


def main(argv: list[str]) -> int:
    source = RECORD.read_text(encoding="utf-8")
    blueprint = BLUEPRINT.read_text(encoding="utf-8")
    new = render(blueprint, source)
    if "--check" in argv:
        if new != blueprint:
            print("docs/blueprint.md §6.2: the generated event table is out of date; run this script")
            return 1
        return 0
    BLUEPRINT.write_bytes(new.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
