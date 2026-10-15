<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Fairflow: state history

`/save-state` appends one entry per save; earlier entries are never edited. The current state is `docs/context/state.md`.

## 2026-10-15 3754cd0

First entry, written from the project memory and from `gh`. Since 2026-10-13, these were merged:
- the veto and re-vote (ADR 0015) and the server-timed negotiation (ADR 0014), with their expiry rules;
- the Authority-only `propose`;
- the generated §6.2 event table;
- the Wake Lock and interrupted-state work (E7);
- CI and test timeouts;
- break tests and docs debt.

The pre-session linking code (#30, ADR 0016) is a draft awaiting the maintainer's read. Four items wait for a design session after the weekend (handoff §9 item 5).

## 2026-10-15 6e0ab1b

#39 merged:
- ADR 0015's season-1 question is decided: a vetoed default still applies.
- `/save-state` and this state page were added.

#30 was updated to the maintainer's third answers (a duplicate linking code refuses the join; the Authority gives no code) and stays a draft at `4b452d3`. It waits for the maintainer's read of ADR 0016, with two review notes. Issue #20 records the maintainer's attribution of the local stall to memory pressure, with the rerun times. The design-session items (handoff §9 item 5) are unchanged.
