<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0005 — v1.0 re-plan after ADR 0002 (room mode in v1.0)

- Status: **proposed**, 2026-10-07. Amends blueprint §8.1–8.3 and §1.4. Needs the maintainer's approval.
- Context: ADR 0002 made room mode (QR join, Python engine on a server) the primary v1.0 mode, with one-phone table mode as the offline fallback. The §8.2 day-by-day plan assumed table mode only and a TypeScript engine. Several epics are now done ahead of that plan; others changed shape.

## Where each v1.0 epic stands (evidence: the repository and CI on `main`)

| Epic (§8.1) | Status | Evidence / what remains |
|---|---|---|
| E1 Engine core | **Done** except the user-defined lens grammar and the debrief brief | Python engine reproduces every §3 number (CI); TypeScript mirror reproduces 454 golden vectors and 454 verdicts |
| E2 Schema and scenarios | **Done** for the default basin | JSON Schema, loader, §5.2 hard checks; Balotra and Mwea scenarios not yet written (E9 data) |
| E3 Event store and replay | **Done on the server** (Python Season Record, projections, commitments, `audit`) | Not yet in the TypeScript mirror, so offline table mode cannot run (see new E3b) |
| E10 Relay and room mode | **Done** (pulled forward from v1.1) | Room server with OWASP protections; end-to-end privacy test over WebSockets |
| E4 Core screens | **Started** (S2–S4 in room mode) | S6 private turn, S7 reveal, S8 game end remain |
| E5 Onboarding and debrief | Not started | S2 pre-session flow is partly covered by the room join; S9, S10, season 0 remain |
| E6 Builder (reduced) | Not started | The loader already gives the Builder its validation |
| E7 PWA and robustness | Not started | Service worker, Wake Lock, reconnection to the room server |
| E8 Balance harness | Not started | The Python engine can now be called directly; `engine serve` stays for other languages |
| E9 Content | Not started (domain lead) | Floor-rule working labels in `content/floor-rules.json` (ADR 0003) |
| **E3b (new)** Table-mode fallback | Not started | Port the Season Record to the TypeScript mirror, verified against Python-generated *record* vectors, as the engine mirror is |

## Proposed order for the remaining four weeks

The blueprint's gates are kept exactly: paper pilot at the end of week 1, app pilot 1 (the cohort-cut decision) at the end of week 3, app pilot 2 in week 4, and the §1.5 definition of done at the tag.

| Week | Engine and data | Client | Domain lead | Gate |
|---|---|---|---|---|
| 1 | Lens previews and band words from the engine; debrief brief; balance harness skeleton (E8) | S2–S4 in room mode; facilitator and projector views | Role and lens cards; floor-rule labels; consent text | **Paper pilot** (unchanged) |
| 2 | E3b: Season Record in the mirror with record vectors; reconnection support on the server | S6 private turn, S7 reveal (ADR 0004 display), S8 game end | Knowledge items, forms A and B | A season end to end on phones in room mode |
| 3 | Balance baseline in CI (§9.2); persistence for research records (Tier 3: DPIA screening, retention) | S9 debrief, S10 review, season 0; E7 PWA and offline table mode on the mirror | Facilitator script v2 | **App pilot 1**: full 120-minute session in room mode; **cohort-cut decision** |
| 4 | Fixes; performance budgets (§7.4); replay audit of pilot records | Fixes; accessibility pass (WCAG 2.2 AA); reduced Builder (E6) if not cut | App pilot 2 | **v1.0 tag** at the §1.5 definition of done |

## Cohort-cut list (§8.3), revised

The six §8.3 items stay. Proposed additions, to be decided at app pilot 1 as before:
1. **Offline table mode (E3b and its screens).** If room mode passes both pilots on the venue network, table mode can move to v1.1, with the facilitator's printed script as the fallback for a network failure. Risk: a session that loses Wi-Fi cannot continue on the app.
2. **The reduced Builder (E6).** Scenarios can be authored as JSON and checked by the loader until v1.1.

## Consequences

- §1.4: room mode and the relay move to v1.0; the v1.1 gate "room mode passes the 120-minute timetable" moves to v1.0 app pilot 1.
- Effort: the §8.3 estimate (32–36 developer-days) was made for the old scope. A new estimate is for the team to make; this ADR does not invent one.
- The research gates (§10) are unaffected.
