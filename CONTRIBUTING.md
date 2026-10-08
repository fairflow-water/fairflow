<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Contributing to Fairflow

Thank you. Fairflow is a teaching and research tool, so two rules carry more weight here than in most projects: **every number has a source**, and **nothing but the engine computes a number**.

## The one rule about parameters

A change to any parameter in `packages/scenarios/` or to any equation in `packages/engine-py/` (the authoritative engine) or its TypeScript mirror `packages/engine/` is a pull request that, in the same PR:

1. updates the scenario file **and** its `source` string (for the default basin, through `packages/engine-py/analysis/kelvara_basin.py`), and the blueprint §2.2 row;
2. updates the affected fixtures in `packages/engine/fixtures/` (both the v1 set and the β set) and says in the PR why the old values were wrong or the new ones better;
3. re-runs the balance baseline once the balance harness exists (planned, ADR 0005) and attaches the report;
4. is reviewed by the science reviewer (see GOVERNANCE.md) before merge.

A PR that changes a number without a source will be closed with a pointer to this paragraph, politely.

## Ways to contribute

- **Scenarios**: a new basin as `scenario.json` with every field sourced, validated by `packages/engine-py/src/fairflow_engine/scenario.schema.json` and the loader's checks. A hypothetical basin uses typical literature values and says so; real cases are labelled as such. Scenarios should meet the balance criteria (blueprint §9.2).
- **Content**: the review form and floor-rule labels in `content/`; role cards, lens-card backs and translations are planned. Word budgets are in blueprint §5.1; content is CC BY 4.0, so your name goes in the file header.
- **Code**: see `docs/blueprint.md` §7 for the module boundaries. The Python engine in `packages/engine-py` is authoritative (ADR 0002); the TypeScript mirror reproduces it on golden vectors. Clients render projections and submit intents. Privacy projections (§6.2 visibility classes) are tested on every build — a PR that makes a sealed field reachable from a public view fails CI.
- **Research**: pre-registrations are linked from `docs/research.md`; a research-data repository is planned per approved cohort.

## Licensing of contributions

By contributing you agree that code is released under MIT and documentation/content under CC BY 4.0 (the Developer Certificate of Origin applies; sign off commits with `git commit -s`). Add an SPDX header to every new file; `reuse lint` must pass.

## Decisions

Anything that changes a rule (R1–R20), a learning outcome, a gate or the session timetable gets an ADR in `docs/decisions/` in the same PR.
