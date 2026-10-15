# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2: write the table of the events record.py emits into docs/blueprint.md, between the generated-table
markers, by reading the `_emit` calls with `ast`: type, the role permitted to cause it, visibility, and the payload
fields one level deep. `--check` exits 1 when the blueprint is out of date; tests/test_event_table.py runs the same
comparison in CI.

The permitted role comes from the emitting handler's `_need` checks on `actor`. Where the code cannot show it (a
role written by the engine for a scheme, or a check made through a flag), ROLE_NOTES says it, with the reason. A field
marked `?` is present only sometimes. A payload built in another function is named by the expression that builds it.
Planned events the engine does not emit yet are a hand-written list after the table, which the test keeps disjoint."""

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
PLANNED = "**Not yet emitted.**"  # the hand-written list of planned events that follows the table

SCHEME = "irrigation scheme"
# (event, actor expression) -> the permitted role, where `_need` on `actor` does not show it; each with its reason
ROLE_NOTES = {
    ("research.consent", "actor"): f"{SCHEME} (asked only of schemes while research is enabled; ADR 0011)",
    ("private.opened", "x.id"): f"each {SCHEME} (written by the engine)",
    ("action.played", "role"): f"the server's timer, for an {SCHEME} (ADR 0013)",
    ("goal.result", "goal['role']"): f"each {SCHEME} (written by the engine at game end)",
}
NEEDS = {  # an `actor` check in the handler -> the permitted role
    "actor == AUTHORITY": "authority",
    "actor in self._scheme_roles()": SCHEME,
    "actor in [*self._scheme_roles(), AUTHORITY]": f"{SCHEME} or authority",
    "actor == ENGINE": "engine",
}


@dataclass
class Field:
    name: str
    always: bool
    children: list[str] | None = None


@dataclass
class Row:
    actors: list[str] = field(default_factory=list)
    visibility: list[str] = field(default_factory=list)
    sites: list[list[Field]] = field(default_factory=list)


def _module_tuples(tree: ast.Module) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Tuple) and len(n.targets) == 1:
            target = n.targets[0]
            if isinstance(target, ast.Name):
                out[target.id] = [e.value for e in n.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return out


def _actor(kind: str, node: ast.expr, func: ast.FunctionDef) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name) and node.id == "AUTHORITY":
        return ["authority"]
    if isinstance(node, ast.IfExp):
        return _actor(kind, node.body, func) + _actor(kind, node.orelse, func)
    text = ast.unparse(node)
    if (kind, text) in ROLE_NOTES:
        return [ROLE_NOTES[(kind, text)]]
    if text == "actor":
        for call in ast.walk(func):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "_need":
                check = ast.unparse(call.args[0])
                if check in NEEDS:
                    return [NEEDS[check]]
        return ["any seated role (no `actor` check)"]
    return [f"`{text}`"]


def _keys(node: ast.expr | None, func: ast.FunctionDef, tuples: dict[str, list[str]]) -> list[str] | None:
    """The keys a dict-valued expression has: a literal, a comprehension over a module tuple, or a local name built
    from those and then extended with item assignments or .update({...})."""
    if isinstance(node, ast.Dict):
        return [k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    if isinstance(node, ast.DictComp) and node.generators and isinstance(node.generators[0].iter, ast.Name):
        found = tuples.get(node.generators[0].iter.id)
        return list(found) if found is not None else None
    if isinstance(node, ast.Name):
        keys: list[str] | None = None
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == node.id for t in n.targets):
                keys = _keys(n.value, func, tuples)
            elif keys is not None and isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == node.id:
                        if isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
                            keys.append(t.slice.value)
            elif keys is not None and isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if n.func.attr == "update" and isinstance(n.func.value, ast.Name) and n.func.value.id == node.id:
                    keys += _keys(n.args[0], func, tuples) or []
        return keys
    return None


def _assigned(func: ast.FunctionDef, name: str) -> ast.expr | None:
    for n in ast.walk(func):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return n.value
    return None


def _fields(
    node: ast.expr | None, func: ast.FunctionDef, tuples: dict[str, list[str]], always: bool = True
) -> list[Field] | None:
    """Top-level payload fields, each with its own keys one level down when the code shows them."""
    if isinstance(node, ast.IfExp):
        one, two = _fields(node.body, func, tuples, False), _fields(node.orelse, func, tuples, False)
        return None if one is None or two is None else one + two
    if isinstance(node, ast.Name):
        return _fields(_assigned(func, node.id), func, tuples, always)
    if not isinstance(node, ast.Dict):
        return None
    out: list[Field] = []
    for k, v in zip(node.keys, node.values, strict=True):
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out.append(Field(k.value, always, _keys(v, func, tuples)))
        elif k is None:  # **spread
            inner = _fields(v, func, tuples, always)
            out += inner if inner is not None else [Field(f"…{ast.unparse(v)}", always)]
    return out


def _rows(source: str) -> dict[str, Row]:
    tree = ast.parse(source)
    tuples = _module_tuples(tree)
    rows: dict[str, Row] = {}
    for func in [f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)]:
        for call in ast.walk(func):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "_emit"):
                continue
            kind = call.args[0]
            if not (isinstance(kind, ast.Constant) and isinstance(kind.value, str)):
                continue
            row = rows.setdefault(kind.value, Row())
            for a in _actor(kind.value, call.args[1], func):
                if a not in row.actors:
                    row.actors.append(a)
            vis = call.args[2]
            v = vis.value if isinstance(vis, ast.Constant) else ast.unparse(vis)
            if v not in row.visibility:
                row.visibility.append(v)
            payload = _fields(call.args[3], func, tuples)
            built = [Field(f"(built by `{ast.unparse(call.args[3])}`)", True)]
            row.sites.append(payload if payload is not None else built)
    return rows


def _payload(sites: list[list[Field]]) -> str:
    merged: dict[str, Field] = {}
    for site in sites:
        for f in site:
            m = merged.setdefault(f.name, Field(f.name, True, None))
            if f.children is not None:
                m.children = (m.children or []) + [c for c in f.children if c not in (m.children or [])]
    out = []
    for name, f in merged.items():
        if name.startswith("("):
            out.append(name)
            continue
        always = all(any(g.name == name and g.always for g in site) for site in sites)
        text = f"`{name}{'' if always else '?'}`"
        if f.children:
            text += " (" + ", ".join(f"`{c}`" for c in f.children) + ")"
        out.append(text)
    return ", ".join(out)


def table(source: str) -> str:
    """The generated markdown table for a record.py source text, in the order record.py first emits each type."""
    lines = ["| Event | Permitted role | Visibility | Payload fields (one level deep) |", "|---|---|---|---|"]
    for kind, row in _rows(source).items():
        lines.append(f"| `{kind}` | {' or '.join(row.actors)} | {' or '.join(row.visibility)} | {_payload(row.sites)} |")
    return "\n".join(lines)


def emitted(source: str) -> list[str]:
    return list(_rows(source))


def current_block(blueprint: str) -> str | None:
    if BEGIN not in blueprint:
        return None
    return blueprint.split(BEGIN, 1)[1].split(END, 1)[0].strip()


def planned(blueprint: str) -> list[str]:
    """Event types in the hand-written 'Not yet emitted' list that follows the generated table."""
    after = blueprint.split(PLANNED, 1)[1]
    items = [line for line in after.splitlines()[1:] if line.strip()]
    out = []
    for line in items:
        if not line.startswith("- `"):
            break
        out.append(line.split("`")[1])
    return out


def render(blueprint: str, source: str) -> str:
    if BEGIN not in blueprint:
        raise SystemExit("docs/blueprint.md §6.2 has no generated-table markers")
    head, rest = blueprint.split(BEGIN, 1)
    return head + f"{BEGIN}\n{table(source)}\n{END}" + rest.split(END, 1)[1]


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
