<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# JOSS submission plan (engine paper, at the v1.1 tag)

Why: short (≤ 1000 words), peer-reviewed, citable with a DOI, and the review is a public code audit of the
claims solver, welfare functions and privacy projections. It is cited from the later serious-game paper so
the methods are already reviewed.

Checklist (JOSS submission requirements, as of 2026 — re-check at submission):
- [x] Open licence (MIT)
- [ ] Repository public with issue tracker — on v1.0 tag
- [ ] Substantial scholarly effort: engine + harness, ≥ 3 months, tests, docs — v1.1
- [ ] `paper.md` + `paper.bib` in `paper/` — skeleton here
- [ ] Automated tests runnable by the reviewer (`pytest` in `packages/engine-py`, `npm test` for the mirror; `scripts/check-all.sh` runs everything)
- [ ] API documentation (typedoc) and a worked example reproducing blueprint §3 fixtures
- [x] Contribution guidelines, code of conduct
- [ ] Archive the reviewed tag on Zenodo; put the DOI in the paper
- [ ] Authors: engine contributors; source-study co-authors acknowledged, not listed, unless they contribute code

Scope discipline: the paper describes software, not learning outcomes. No claim about students; cohort
evidence goes to Simulation & Gaming or HESS after two cohorts (blueprint §10).
