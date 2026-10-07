---
title: 'Fairflow engine: a claims-problem allocator with a posteriori justice scoring for water-sharing games'
tags:
  - Python
  - TypeScript
  - water allocation
  - distributive justice
  - bankruptcy problems
  - serious games
authors:
  - name: Seleshi Yalew
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: IHE Delft Institute for Water Education, the Netherlands
    index: 1
date: 2026-12-01
bibliography: paper.bib
---

<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- JOSS expects 250–1000 words; re-check the required sections at submission (they have changed). Scope: the engine and the balance harness, not the game's learning claims. ORCID is a placeholder. -->

# Summary

`fairflow-engine` is a Python library (NumPy, SciPy) that turns a basin description — river inflow, a protected reserve, a shared aquifer that rejects recharge when full [@Theis1940; @KonikowLeake2014], and three to five irrigation schemes with demands, capacities, yield-response coefficients and populations — into seasonal allocations under nine principles of distributive justice expressed as claims-problem rules [@Thomson2003; @AumannMaschler1985], FAO-33 crop production [@DoorenbosKassam1979], two equity indicators with a switchable equalisandum, economic water productivity and a use-over-renewable-supply sustainability ratio, and five a posteriori welfare functions (utilitarian, prioritarian in Atkinson's isoelastic form [@Atkinson1970], sufficientarian, egalitarian, capability-weighted). It records every decision as an append-only event log with per-field visibility classes, so that a game is reproducible from its record; individual private actions are not displayed before the debrief, and a feasibility audit shows they cannot be computed from what is displayed beyond what the public total implies (ADR 0004). It is the computational core of Fairflow, a serious game on the water–energy–food nexus [@Yalew2024], and runs on the room server and in a Monte-Carlo balance harness; a TypeScript port for offline play on a phone must reproduce Python-generated golden vectors in continuous integration (ADR 0002).

# Statement of need

Teaching and research on water allocation equity need a model in which the allocation rule, the equity metric and the welfare evaluation are all explicit, swappable and traceable to literature — and in which a classroom game and a research simulation share one implementation. Bankruptcy rules have been applied to transboundary allocation [@Madani2014], but existing tools either hard-code one rule, compute indicators outside the game, or cannot reproduce a session from its log. `@fairflow/engine` provides (i) a generic claims-problem solver with weights, floors and a value maximiser from which the classical rules are configuration; (ii) indicators and welfare functions with stated axioms and known failure modes; (iii) an event-sourced record with a privacy projection test; and (iv) an NDJSON worker mode used by the companion `fairflow-balance` harness to run tens of thousands of agent games per scenario.

# Functionality

<!-- allocate · resolveSeason · indicators · welfare · verdict · stability · criterion grammar · applyEvent and projections · engine serve. One paragraph each, with the reference vectors of blueprint §3 as the worked example. -->

# Verification

<!-- fixtures (two sets), property tests, replay determinism across JavaScriptCore and V8, privacy projection test, balance criteria. -->

# Acknowledgements

<!-- reviewers, source-study co-authors, students of the first cohort (collectively). -->

# References
