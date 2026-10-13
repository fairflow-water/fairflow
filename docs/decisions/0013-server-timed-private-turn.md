<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0013: The server times the private turn

- Status: **accepted by the maintainer 2026-10-12** (plan approved with these choices: a 10 s grace, the phone's own timer commit flagged too and told apart from the server's, no timeout indication on any screen during play, no mid-season end). Field names set by the maintainer on 2026-10-13: `autoCommitted` and `autoCommittedBy`, the §6.2 name.
- Amends R20 (who runs the private-turn timer in room mode) and the `action.played` row of blueprint §6.2. First part of issue #9.

## Context

R20 sets the private turn: "private turn 0:45 from the receiver's tap, auto-commit with a 3 s undo toast". The scenario carries it as `session.decisionS` (blueprint §5.0: `"decisionS": 45`). In room mode, only the phone ran the timer (`PrivateTurn.tsx`):

1. **What it commits.** At zero, the phone commits the player's current choice. Untouched, that is the first offered level and no action. The levels are "0..cap" (R10) and start at 0, so the first level is 0 pumps, also for a scheme whose wells are dry (cap 0).
2. **A phone that is gone never commits.** A season resolves only when every scheme has committed (R11), so a dead, lost or locked phone stalls the season for the whole table.
3. **The time-box cannot help.** `game.timeboxed` ends play "after the current season" (R20), and that season never ends.
4. **A reload restarts the 45 s**, because the phone's timer starts when the screen appears.
5. **A commit could be lost on a dropped connection** and the turn never committed again (fixed separately, PR #10).

The engine record had no way to tell a timed-out commit from a chosen one. Blueprint §6.2 lists an `autoCommitted` field for `action.played`, but no recorded field was ever implemented.

## Decision

1. **The server holds the deadline.**
   - The private turn opens when the engine emits `private.opened` for the season. The record time `t` of that event is the start.
   - The phone's deadline is the start plus `session.decisionS`.
   - The server's deadline is the phone's deadline plus a **grace**, so that a connected phone, which fires at its own deadline, always wins.
   - In room mode, every phone receives its private turn at the same moment, so the start is `private.opened`, not a hand-over tap (`handoverStartsTimer` concerns table mode).
   - A scenario without `decisionS` has no timer on either side, as before.

2. **The grace.**

   | Parameter | Value |
   |---|---|
   | Server grace after the private-turn deadline | 10 s (maintainer convention, 2026-10-12) |

   - It is registry parameter `session.privateTurnGraceS`, which quotes the row above. A scenario may override it in `session.privateTurnGraceS`.
   - It is not a model parameter and changes no number in the game.

3. **The default is the untouched phone's.** When the server's deadline passes, under the room's lock, the engine commits for every scheme that has not committed:
   - the first level that scheme was offered in its `private.opened` (0 pumps);
   - and no action.

   The season then resolves as usual.

4. **The phone counts down to the server's deadline.**
   - The server's `welcome` message carries the server's time. The phone corrects for its own clock difference and counts down to "start + `decisionS`".
   - A reload or reconnection therefore continues the same countdown instead of restarting it.
   - At zero, the phone still commits the player's current choice, as before. The 3 s undo is unchanged.

5. **Which side fired is recorded.**
   - A commit made by a timer adds `autoCommitted: true` and `autoCommittedBy` to `action.played`. `autoCommittedBy` is `"phone"` for the phone's own timer and `"server"` for the server's.
   - A commit the player made is unchanged: the two fields are absent.
   - `autoCommitted` is the name §6.2 gives this field. The phone's commit intent carries `autoCommitted: true` when its own timer fired. (`lens.chosen` keeps its own `byTimeout` for the vote timer, R8.)

6. **A host-only intent.** The server's commit is a new engine intent, `timeout_private {season}`:
   - It is accepted only from the actor `engine`, and only in the private phase of the named season. A stale timer for an earlier season is refused.
   - It is not part of the client protocol, so no phone, display or facilitator can send it.
   - It writes one `action.played` per missing scheme. The event's actor is that scheme's role, as for its own commit, so the scheme's projection and the season's resolution work unchanged.
   - It applies to the practice round (season 0) too.

7. **No indication during play.**
   - A server timeout implies 0 pumps, so showing it would disclose a private action (ADR 0004).
   - `autoCommitted` and `autoCommittedBy` are therefore withheld from every projection until a per-player debrief, including the scheme's own projection.
   - A totals-only debrief never shows them.
   - The server-side record keeps them, for audit and a future research export.
   - No screen shows that a scheme timed out. A plain "phone disconnected" indicator belongs to issue #9, not to this decision.

8. **R20 stands.**
   - The time-box still ends play only after the current season. A game is never ended mid-season, so the hash reveal sequence is unbroken.
   - With the server's deadline, the current season always resolves, so a time-box with a seat absent now ends the game. From a private turn, that takes at most the remaining `decisionS` plus the grace.

## Relation to the blueprint (for the maintainer)

- §6.2 names the flag `autoCommitted`, and this decision keeps that name (maintainer, 2026-10-13). It adds `autoCommittedBy`, so that the phone and the server can be told apart, as decided.
- The §6.2 row now points here. Its text is not rewritten.

## Consequences

- **Game record.**
  - `action.played` may carry two more fields. Its visibility class stays `sealed`.
  - The engine has one more intent. The set of event types is unchanged.
  - Records made before this decision replay and audit unchanged: an absent `autoCommitted` means a commit the player made.
  - `audit` recomputes seasons from the recorded pumps, so it is unaffected.
- **What a 0 means.**
  - A server-timed 0 means the phone was absent, not that the player chose 0.
  - A phone-timed commit means the player let the clock run; its choice is their last selection.
  - An analysis must keep these apart. The fields are there for that, and the §6.3 codebook needs a line for them when the research export is built.
- **The phone's flag is the phone's claim.** A modified client could set or omit `autoCommitted` on its own commits. It describes how the commit was made; it is not proof. The server's flag is set by the server alone.
- **A residual signal.** A season that resolves exactly at the server's deadline tells the table that some scheme was committed by the server, though not which. At a physical table, an absent player is visible anyway. A season that resolves at the phone's deadline says that some phone's timer ran out, with its own choice.
- **Not decided here:** moving a seat to another phone and a "phone disconnected" indicator (issue #9).

## Sources

- Blueprint R8, R10, R11, R20, §5.0 (session JSON) and §6.2.
- ADR 0004 (in-play disclosure).
- Issue #9 and PR #10.
