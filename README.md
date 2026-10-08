<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Fairflow

A serious game of distributive justice in water allocation — the entry point of the EquiNex Spatial Equity Modeling Suite (IHE Delft).

Three to five water users and a basin authority share a river and an aquifer over five or six seasons in a hypothetical basin (the Kelvara basin, ADR 0007), vote each season on which principle of justice decides the split, act privately on what they receive, and are scored together on equity, efficiency and sustainability. *There is no lens-free way to share scarce water.*

## Licence — two parts

| What | Where | Licence |
| --- | --- | --- |
| Code (Python engine, TypeScript mirror, room server, UI, CI) | `packages/`, `scripts/`, `.github/` | [MIT](LICENSE) |
| Documentation, teaching content, scenarios, fixtures | `docs/`, `content/`, `packages/scenarios/*.json`, `packages/engine/fixtures/` | [CC BY 4.0](LICENSE-docs) |

Every file carries an `SPDX-License-Identifier`; CI enforces [REUSE](https://reuse.software) compliance. Participant data are never in this repository (see `fairflow-water/fairflow-data`).

## Cite

See [`CITATION.cff`](CITATION.cff) (GitHub shows a "Cite this repository" button). Each tag is meant to receive a Zenodo DOI once the Zenodo integration is set up; Zenodo reads `CITATION.cff`. A JOSS paper describing the engine is drafted in `paper/`, to be submitted at v1.1.

## Documents

- [Development blueprint](docs/blueprint.md) — the build contract: model, rules, screens, data, architecture, roadmap, V&V, research design, grounding.
- [Decisions](docs/decisions/) — why things are the way they are.

## What is in this repository

- `packages/engine-py`: the authoritative Python engine (ADR 0002), with its tests and analyses.
- `packages/engine`: the TypeScript mirror, checked against golden vectors from the Python engine.
- `packages/server`: the room server (FastAPI, WebSockets).
- `packages/ui`: the web client (React).
- `packages/scenarios`: the Kelvara scenario and the sourced parameter registry.

Planned, not yet created: a balance harness, a scenario builder, a research-data repository (per approved cohort).

## Setting up REUSE locally

```sh
pipx install reuse
reuse download --all   # fetches the licence texts into LICENSES/
reuse lint
```
