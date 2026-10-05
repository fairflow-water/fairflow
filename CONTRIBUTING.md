<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Contributing to Fairflow

Thank you. Fairflow is a teaching and research tool, so two rules carry more weight here than in most projects: **every number has a source**, and **nothing but the engine computes a number**.

## The one rule about parameters

A change to any parameter in `packages/scenarios/` or to any equation in `packages/engine/` is a pull request that, in the same PR:

1. updates the scenario file **and** its `source` string (or the blueprint §2.2 row);
2. updates the affected fixtures in `packages/engine/fixtures/` (both the v1 set and the β set) and says in the PR why the old values were wrong or the new ones better;
3. re-runs the balance baseline (`fairflow-balance`, tier *baseline*) and attaches the report;
4. is reviewed by the science reviewer (see GOVERNANCE.md) before merge.

A PR that changes a number without a source will be closed with a pointer to this paragraph, politely.

## Ways to contribute

- **Scenarios**: a new basin as `scenario.json` with every field sourced. Use the Scenario Builder's export; the schema will tell you what is missing. Scenarios ship only if they pass the balance criteria (blueprint §9.2) or carry the Builder's warning.
- **Content**: role cards, lens-card backs, translations. Word budgets are in blueprint §5.1; content is CC BY 4.0, so your name goes in the file header.
- **Code**: see `docs/blueprint.md` §7 for the module boundaries. The engine is pure TypeScript with no DOM; shells render projections and submit intents. Privacy projections (§6.2 visibility classes) are tested on every build — a PR that makes a sealed field reachable from a public view fails CI.
- **Research**: analysis code over the frozen export schema goes to `fairflow-data`; pre-registrations are linked from `docs/research.md`.

## Licensing of contributions

By contributing you agree that code is released under MIT and documentation/content under CC BY 4.0 (the Developer Certificate of Origin applies; sign off commits with `git commit -s`). Add an SPDX header to every new file; `reuse lint` must pass.

## Decisions

Anything that changes a rule (R1–R20), a learning outcome, a gate or the session timetable gets an ADR in `docs/decisions/` in the same PR.
