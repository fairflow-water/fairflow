<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0002 — Python is the authoritative engine; the phone runs a verified mirror

- Status: **accepted** by the maintainer, 2026-10-06. Amends blueprint §7.1–7.2, §1.4 and §8.2. The v1.0 sprint plan (§8.2) must be re-planned for room mode in v1.0; that re-plan is a separate decision.
- Context:
  - The maintainer requires that no number or equation is produced by an LLM or typed without a source, and that all model calculations are grounded in Python (numpy/scipy) for scientific credibility.
  - Participants should join on a phone or laptop by scanning a QR code on the facilitator's screen. Lecturers should be able to run either short exercises or the full game.
  - Offline play (one shared phone, no network) remains a requirement for venues with poor Wi-Fi.
  - The blueprint v3.1 specified a single TypeScript engine (§7).
- Research (2026-10-05, sources in the session report):
  - **Pyodide 314.0.7:** about 6 MB core, plus about 3 MB for numpy and about 14 MB for scipy (Brotli). `scipy.optimize.milp` works in it. There are no reliable phone load-time figures, and iOS WebAssembly has open memory issues.
  - **Flet 1.0:** released 2026-09; too new, and has no rooms or QR join.
  - **oTree:** a strong fit for lab experiments, a poor fit for a facilitated 120-minute game.
  - **FastAPI + WebSockets:** gives full control over server-held sealed state and reconnection, and handles about 40 clients per room in one process.
  - The "Python is authoritative, ports must match its golden vectors" pattern is established practice (the Ethereum consensus specification is the best-known case).

## Decision

1. **`fairflow-engine` (Python, `packages/engine-py`) is the authoritative implementation of blueprint §2.** It uses numpy and scipy (`scipy.optimize.milp` for the value maximiser, `scipy.optimize.brentq` for equal sacrifice). Every function cites its section. No parameter has a default in code.
2. **Numbers come only from sources, checked by Python in CI:**
   - Expected values are parsed directly from `docs/blueprint.md`. Each is checked to half a unit of its last printed digit.
   - The fixture files must equal the blueprint.
   - Parameter defaults live in `packages/scenarios/parameters.json`, each with a verbatim blueprint quote that CI must find in the blueprint. Where the blueprint states no default, the value is `null` until the maintainer sets it.
   - A computed result that contradicts the blueprint is reported as a finding to the science reviewer, never silently "fixed".
3. **Room mode (QR join on a phone or laptop) is the primary mode.** A FastAPI + WebSockets server runs the Python engine live and holds sealed fields (§6.2), so every number a participant sees comes from Python.
4. **Table mode (one phone, offline) is the fallback.** It runs the TypeScript engine as a *mirror* of the Python engine:
   - The mirror must reproduce a Python-generated golden-vector corpus within the §7.2 rounding, in CI.
   - It contains no numeric literals beyond declared tolerances.
   - Every exported table-mode record is replayed by the Python engine before it enters a research dataset.
   - Pyodide may replace the mirror later, if a test on real phones meets §7.4.
5. **Exercises:** an exercise is a scenario plus a subset of screens and seasons, each with its own room code or QR, mapped to one learning outcome. The full game is one exercise among them.

## Consequences

- §7.1: `@fairflow/engine` (TypeScript) is renamed in role to the "mirror". The relay (§7.1) becomes a Python service and is pulled forward from v1.1 to v1.0.
- §1.4 and §8.2: room mode moves to v1.0 and table mode becomes the fallback. The v1.0 sprint plan needs re-planning; this ADR does not do it.
- §7.4: the room-mode budget (< 150 ms intent to projection) now applies to v1.0.
- CI gains a Python job; CONTRIBUTING's "nothing but the engine computes a number" now means the Python engine.
- Open for the maintainer:
  - accept or amend this ADR;
  - the `null` registry defaults (`indicators.welfareGamma`, `lenses.sufficientarian.floorScaling`);
  - the exercise list.
