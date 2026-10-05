<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# fairflow-engine

The authoritative implementation of the Fairflow model (blueprint §2) and its Season Record (§6.2), in Python with
NumPy and SciPy. Every expected value in its tests is read from `docs/blueprint.md`; every model parameter comes from a
scenario or the sourced registry `packages/scenarios/parameters.json` (ADR 0002).

```sh
uv sync --locked          # exact, locked environment
uv run pytest             # tests + coverage gate
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run python scripts/generate_vectors.py   # golden vectors for the TypeScript mirror
```
