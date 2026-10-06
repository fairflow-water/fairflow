# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""The parameter registry may only contain defaults that the blueprint states, verbatim."""

import json
import re

import pytest
from blueprint import BLUEPRINT, ROOT

REGISTRY = json.loads((ROOT / "packages" / "scenarios" / "parameters.json").read_text(encoding="utf-8"))
PARAMS = REGISTRY["parameters"]


def printed_forms(value) -> set[str]:
    """How a default may be printed in the quote: 2 / 2.0, 0.90 / 0.9, max_value as "max value"."""
    if isinstance(value, str):
        return {value, value.replace("_", " ")}
    return {f"{value:g}", f"{value:.1f}", f"{value:.2f}"}


def test_keys_unique():
    keys = [p["key"] for p in PARAMS]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("p", PARAMS, ids=lambda p: p["key"])
def test_quote_is_verbatim_in_blueprint(p):
    """Quotes come from docs/blueprint.md, or from the decision record named in `sourceFile`."""
    source = (ROOT / p["sourceFile"]).read_text(encoding="utf-8") if "sourceFile" in p else BLUEPRINT
    for field in ("quote", "alsoQuote"):
        if field in p:
            assert p[field] in source, (
                f"{p['key']}: {field} not found verbatim in {p.get('sourceFile', 'docs/blueprint.md')}"
            )


@pytest.mark.parametrize("p", PARAMS, ids=lambda p: p["key"])
def test_default_is_printed_in_its_quote(p):
    value = p["default"]
    if value is None:
        assert p.get("decision"), f"{p['key']}: a null default must say why (field 'decision')"
        return
    tokens = set(re.findall(r"[\w.]+", p["quote"].replace("–", " ").replace("·", " ")))
    for v in value if isinstance(value, list) else [value]:
        assert printed_forms(v) & (tokens | {p["quote"]} | set(p["quote"].split(" / "))) or any(
            f in p["quote"] for f in printed_forms(v)
        ), f"{p['key']}: default {v!r} is not printed in its quote"


def test_checks_reject_fabrication():
    """A default not printed in its quote, or a quote not in the blueprint, must fail."""
    fake_value = {"key": "x", "default": 0.7, "quote": "mᵢ = 0.5"}
    with pytest.raises(AssertionError):
        test_default_is_printed_in_its_quote(fake_value)
    fake_quote = {"key": "x", "default": 0.5, "quote": "survival threshold of 0.5 (invented)"}
    with pytest.raises(AssertionError):
        test_quote_is_verbatim_in_blueprint(fake_quote)
