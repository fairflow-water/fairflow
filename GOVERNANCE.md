<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Governance

Fairflow is small and should stay simple to run.

- **Maintainer**: Seleshi Yalew (IHE Delft). Merges, tags, releases, DOIs.
- **Science reviewer**: a named person (initially the maintainer) who must approve any PR touching the authoritative engine `packages/engine-py/src/fairflow_engine/`, the mirror's `packages/engine/src/{allocate,indicators,welfare,verdict,aquifer,production}*`, `packages/scenarios/` (scenarios and the parameter registry), `packages/engine-py/analysis/`, or blueprint §2–§3. The role exists so that the scientific defensibility of the model does not depend on who happens to review a PR.
- **Content reviewer**: approves changes to `content/` against the sources each item cites.
- **Contributors**: anyone, via pull request under CONTRIBUTING.md. Regular contributors may be invited as maintainers of a package.

Rules that do not change without an ADR: no scenario ships without sources; no public projection shows a sealed field before the debrief; no release gate depends on a research result; participant data never enter this repository.

Code of conduct: Contributor Covenant 2.1 (CODE_OF_CONDUCT.md). Reports to the maintainer's address in CITATION.cff.
