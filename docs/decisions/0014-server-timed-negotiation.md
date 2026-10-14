<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0014: The server times the negotiation

- Status: **proposed**, in a draft pull request, for the maintainer's review.
- Implements the negotiation timer of R7, R8 and R20 in room mode, on the pattern of ADR 0013 (the server-timed private turn).

## Context

- **R7:** "The negotiation timer (R20) starts when the lens screen opens."
- **R20:** "Negotiation 3:00 from screen open in seasons 0–2 and 4:00 from season 3." The scenario carries this as `session.negotiationS` (`seasons0to2`: 180, `from3`: 240).
- **R8:** "Timer expiry with no proposal applies the previous season's lens (the scenario's default lens in season 1); `lens.chosen` records `byTimeout`." S4 and §13 row 9 say the same.
- Until now no timer existed. A vote stayed open until the Authority closed it. The engine's `close_vote` already applies the previous lens, with `byTimeout`, when nothing has been proposed.

The blueprint does not say what expiry does when lenses *have* been proposed, or voted on.

## Decision

1. **The server holds the deadline.** The start is the record time `t` of the season's `season.climate`, the moment the lens screen opens for everyone. The deadline is the start plus `negotiationS.seasons0to2` in seasons 0 to 2 and plus `negotiationS.from3` from season 3. A restored room re-arms from the record (ADR 0012), and a deadline that passed while the server was down fires at once.
2. **No grace.** In ADR 0013 the grace lets a connected phone's own timer commit first. No client closes a vote by itself, so the server closes it at the deadline itself. An Authority tap that arrives first wins; one that arrives after is refused as `wrong_phase`.
3. **What expiry chooses.** A host-only engine intent, `timeout_vote {season}` (actor `engine`, not in the client protocol; a stale timer is refused):
   - **A single plurality leader** among the votes cast is chosen, as `close_vote` would choose it.
   - **No proposal, no vote, or a tie:** the previous season's lens applies, or the scenario's default lens in season 1 (R8's rule, extended to these cases). A tie at expiry does not wait for the Authority: the timer exists so that the season goes on.
   - Either way, `lens.chosen` records `byTimeout: true`. It is public, as the field already was.
4. **The practice round is timed too,** with the season 0–2 length. Its fallback is the scenario's default lens, since no season precedes it.
5. **The screens (S4).**
   - The projector, the phones and the facilitator show a bar that shrinks to the server's deadline, on the server's clock (`serverTime` in the welcome, ADR 0013), so a reload continues it.
   - Seconds appear only in the last 30, as S4 says.
   - The bar shows during the vote, not during a tie-break or a floor vote.
6. **Out of scope:** a timer on the tie-break and on the floor vote. The Authority decides those at the table.

## Questions for the maintainer

1. With proposals and votes on the table at expiry, should the plurality leader be chosen (as built), or should the previous lens apply, as when nothing was proposed? A related edge case: one lens proposed and no vote cast. The Authority's `close_vote` takes that lens, but expiry applies the previous lens (as built, since nobody voted for it).
2. Should a tie at expiry go to the previous lens (as built) or wait for the Authority's tie-break?
3. Should the practice round be timed (as built)?

## Consequences

- One more engine intent (`timeout_vote`, host only). No new event type and no new field: `lens.chosen.byTimeout` already exists.
- A scenario's `session.negotiationS`, when present, must give both lengths as positive numbers of seconds, or the scenario does not load. The server computes the deadline from them.
- The server keeps one timer per room, for whichever phase is timed (vote or private turn). A new phase's timer cancels the last one's, which is still asleep.
- A table that talks past the deadline loses the choice to the clock. The facilitator can no longer hold a vote open indefinitely.

## Sources

- Blueprint R7, R8, R20, §5.2 S4, §13 row 9, §5.0 (session JSON).
- ADR 0012 (persistent rooms), ADR 0013 (server-timed private turn).
