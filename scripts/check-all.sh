#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
#
# Run locally every check CI runs, in the same order, and stop at the first failure. Use it before pushing to main:
# an admin push bypasses branch protection, so this is the only gate in front of a direct push.
set -euo pipefail
cd "$(dirname "$0")/.."
step() { printf '\n== %s\n' "$*"; }

step "workflow and config YAML parse"
for f in .github/workflows/*.yml .github/dependabot.yml; do
  uv run --no-project --with pyyaml python -c "import sys, yaml; yaml.safe_load(open(sys.argv[1], encoding='utf-8'))" "$f"
done

step "REUSE"
PYTHONIOENCODING=utf-8 uvx --from "reuse[charset-normalizer]" reuse --no-multiprocessing lint >/dev/null

for pkg in engine-py server; do
  step "$pkg: lock, Ruff, format, mypy, tests"
  (cd "packages/$pkg" && uv sync --locked -q && uv run ruff check . && uv run ruff format --check . >/dev/null \
    && uv run mypy && PYTHONIOENCODING=utf-8 uv run pytest -q --cov -p no:warnings >/dev/null)
done

step "TypeScript: npm ci, lint, build, tests with coverage"
npm ci --no-audit --no-fund >/dev/null
npm run lint -w packages/engine && npm run lint -w packages/ui
npm run build >/dev/null
npm run coverage -w packages/engine >/dev/null && npm run coverage -w packages/ui >/dev/null

step "all checks passed"
