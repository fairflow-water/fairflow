# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Blueprint §6.2: write the table of the events record.py emits into docs/blueprint.md, between the generated-table
markers, by reading the `_emit` calls with `ast`: type, the role permitted to cause it, visibility, and the payload
fields one level deep. `--check` exits 1 when the blueprint is out of date; tests/test_event_table.py runs the same
comparison in CI.

"Caused by" follows the calls from each `_on_<intent>` handler to the method that emits, and names who may send that
intent from the handler's `_need` checks on `actor` (an unrecognised role check stops the script). Where a flag
narrows it further, CAUSE_NOTES says so, with the reason. "Recorded actor" is the `actor` the event stores. A field
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
TIMER = "the server's timer"
NEEDS = {  # a role check on `actor` in an intent handler -> who may send that intent
    "actor == AUTHORITY": "authority",
    "actor in self._scheme_roles()": SCHEME,
    "actor in [*self._scheme_roles(), AUTHORITY]": f"{SCHEME} or authority",
    "actor == ENGINE": TIMER,
}
# event -> who causes it, where the handler's checks do not show it; each with its reason
CAUSE_NOTES = {
    "research.consent": f"{SCHEME} (join; asked only of schemes while research is enabled, ADR 0011)",
    "linking.code": f"{SCHEME} (join; the Authority gives none, ADR 0016)",
}


def _role_check(text: str) -> bool:
    """A `_need` test that limits who may send the intent (not one about the sender's own state)."""
    return text.startswith(("actor ==", "actor !=", "actor in [", "actor in self._scheme_roles"))


def _sender(handler: ast.FunctionDef) -> str:
    for call in ast.walk(handler):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "_need":
            check = ast.unparse(call.args[0])
            if check in NEEDS:
                return NEEDS[check]
            if _role_check(check):
                raise SystemExit(f"{handler.name}: role check {check!r} is not in NEEDS; add it")
    return "any seated role (no `actor` check)"


def _causes(tree: ast.Module) -> dict[str, list[str]]:
    """For each function of record.py, the intents that reach it (`_on_<intent>` handlers and the methods they call,
    followed through `self.<method>(...)`), each named by who may send it."""
    funcs = {f.name: f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    calls = {
        name: {
            c.func.attr
            for c in ast.walk(f)
            if isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and isinstance(c.func.value, ast.Name)
            and c.func.value.id in ("self", "game")
            and c.func.attr in funcs
        }
        for name, f in funcs.items()
    }
    out: dict[str, list[str]] = {name: [] for name in funcs}
    for name, f in funcs.items():
        if not name.startswith("_on_"):
            continue
        cause = f"{_sender(f)} (`{name[4:]}`)"
        seen, todo = set(), [name]
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            out[n].append(cause)
            todo += sorted(calls[n])
    return out


def _actor(node: ast.expr) -> list[str]:
    """The `actor` the event records."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name) and node.id == "AUTHORITY":
        return ["authority"]
    if isinstance(node, ast.IfExp):
        return _actor(node.body) + _actor(node.orelse)
    if ast.unparse(node) == "actor":
        return ["the sender"]
    return ["the scheme concerned"]


@dataclass
class Field:
    name: str
    always: bool
    children: list[str] | None = None


@dataclass
class Row:
    actors: list[str] = field(default_factory=list)
    causes: list[str] = field(default_factory=list)
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
    causes = _causes(tree)
    rows: dict[str, Row] = {}
    for func in [f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)]:
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
            reached = [CAUSE_NOTES[kind.value]] if kind.value in CAUSE_NOTES else causes[func.name] or ["game creation"]
            for c in reached:
                if c not in row.causes:
                    row.causes.append(c)
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
    lines = [
        "| Event | Caused by (who may send the intent) | Recorded actor | Visibility | Payload fields (one level deep) |",
        "|---|---|---|---|---|",
    ]
    for kind, row in _rows(source).items():
        cells = ["; ".join(row.causes), " or ".join(row.actors), " or ".join(row.visibility), _payload(row.sites)]
        lines.append(f"| `{kind}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def emitted(source: str) -> list[str]:
    return list(_rows(source))


def current_block(blueprint: str) -> str | None:
    if BEGIN not in blueprint:
        return None
    return blueprint.split(BEGIN, 1)[1].split(END, 1)[0].strip()


def planned(blueprint: str) -> list[str]:
    """Event types in the hand-written 'Not yet emitted' list that follows the generated table."""
    if PLANNED not in blueprint:
        return []
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
