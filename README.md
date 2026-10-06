<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Fairflow

A serious game of distributive justice in water allocation — the entry point of the EquiNex Spatial Equity Modeling Suite (IHE Delft).

Three to five water users and a basin authority share a river and an aquifer over five or six seasons, vote each season on which principle of justice decides the split, act privately on what they receive, and are scored together on equity, efficiency and sustainability. *There is no lens-free way to share scarce water.*

## Licence — two parts

| What | Where | Licence |
| --- | --- | --- |
| Code (engine, UI, store, builder, relay, schema, CI) | `packages/`, `apps/`, `scripts/`, `.github/` | [MIT](LICENSE) |
| Documentation, teaching content, scenarios, fixtures | `docs/`, `content/`, `packages/scenarios/*.json`, `packages/engine/fixtures/` | [CC BY 4.0](LICENSE-docs) |

Every file carries an `SPDX-License-Identifier`; CI enforces [REUSE](https://reuse.software) compliance. Participant data are never in this repository (see `fairflow-water/fairflow-data`).

## Cite

See [`CITATION.cff`](CITATION.cff) (GitHub shows a "Cite this repository" button). Every tag receives a Zenodo DOI; Zenodo reads `CITATION.cff` directly (there is deliberately no `.zenodo.json`, so there is one file to keep current). The engine is described in a JOSS paper (`paper/`), submitted at v1.1.

## Documents

- [Development blueprint](docs/blueprint.md) — the build contract: model, rules, screens, data, architecture, roadmap, V&V, research design, grounding.
- [Decisions](docs/decisions/) — why things are the way they are.

## Repositories in the organisation

`fairflow` (this), `fairflow-balance` (Python balance harness), `fairflow-pipeline` (WaPOR authoring, v1.2), `fairflow-agents` (Concordia, v2.0), `fairflow-data` (research datasets, per approved cohort), `EMODPS-ogb3` (Omo–Gibe optimisation with justice welfare functions).

## Setting up REUSE locally

```sh
pipx install reuse
reuse download --all   # fetches the licence texts into LICENSES/
reuse lint
```
