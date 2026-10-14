<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0015: The Authority's veto and the re-vote

- Status: **accepted by the maintainer, 2026-10-14** (PR #21). (ADR 0014 is reserved for the negotiation timer.)
- Implements R8's veto. Adds one event type to the Season Record (blueprint §6.2).

## Context

R8: "Plurality wins; the Authority breaks ties and holds one veto per game \[M3: after a permit audit\], after which the remaining lenses are re-voted." Blueprint §6.2 gives `lens.chosen` the optional fields `veto?` and `revote?`, and the v1.0 sprint plan (§8.2, day 2) lists a "veto modal" on S4.

The blueprint leaves open:
- when in the vote the veto is used;
- what happens to the votes already cast;
- whether the practice round has one;
- how the veto itself appears in the record. An event-sourced record needs an event for it, and §6.2 lists none.

## Decision

1. **When.** The Authority vetoes a *proposed* lens while the vote is open (phase `vote`), with the live tally in view. A veto after the vote has closed would need the result held back first. The engine chooses at `close_vote`, so the veto comes before it.
2. **One per game.** A second veto is refused (`veto_used`), in the same season or a later one.
3. **The re-vote.**
   - The vetoed lens leaves the ballot and cannot be proposed again that season (`vetoed`).
   - Every vote cast so far is cleared, so each scheme votes again on the remaining lenses.
   - No new lens may be proposed for the rest of that season (`revote_only`): R8 re-votes "the remaining lenses". Proposals open again in the next season.
   - The vote then closes as usual: plurality, with a tie going to the Authority.
4. **Something must remain.** A veto needs at least one other proposal (`nothing_left`), so a re-vote is always possible.
5. **Not in the practice round** (`veto_not_in_tutorial`). The practice round is not scored, and a veto spent there would cost the game its one veto.
6. **The record.**
   - **New event** `lens.vetoed {lens}`: actor `authority`, visibility `public`. Everyone at the table sees the veto, as they see the Authority's tie-break.
   - **`lens.chosen`** carries the §6.2 fields `veto` (the vetoed lens) and `revote: true` in the season of the veto. They are absent otherwise.
   - Records made before this decision replay unchanged.
7. **M3.** In v1.0 the veto is available once per game without an audit. When Module 3 ships, the veto becomes audit-gated: the permit audit becomes a further condition of the same intent.
8. **The screen (S4).**
   - The Authority's "Veto" sits on each proposed lens and asks for confirmation ("Use the one veto of the game on this lens? Every vote so far is cleared.").
   - Every screen then shows "The Authority vetoed *lens*. Vote again on the remaining lenses." The vetoed row says so and offers no button, and no lens offers Propose.
   - The engine refuses to close a vote of several proposals that has no votes (`no_votes`). After a veto that is every vote, so until a scheme votes again the Authority's screen says why: "The veto cleared every vote. The vote can close once the schemes have voted again on the remaining lenses."

## Maintainer's answers (2026-10-14)

- The veto is used during the vote (decision 1), and every vote is cleared (decision 3).
- M3: in v1.0 the veto is available once per game without an audit; it becomes audit-gated when Module 3 ships (decision 7).
- After a veto, the remaining proposals are re-voted and no new lens may be proposed, per R8 (decision 3).
- The veto screen explains a `no_votes` refusal (decision 8).
- Not raised again: a practice-round veto stays refused (decision 5).

## Consequences

- One more intent (`veto`, Authority only) and one more event type (`lens.vetoed`). The §6.2 table should list it when §6.2 is brought up to date (handoff §6).
- The debrief can name the veto from the record (who decided, R8; blueprint §1.2's procedural-justice theme); it does not yet.

## Sources

- Blueprint R8, §6.2 (`lens.chosen`), §8.2 (S4 veto modal), §1.2 (procedural justice).
- ADR 0003 (players choose value judgements).
