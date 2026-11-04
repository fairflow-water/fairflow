<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0018: Room-mode predictions, the Authority, treatment arms and the service worker

- Status: **accepted by the maintainer, 2026-11-03.** The choices come from the design session for handoff §9 item 5 (2026-10-29 and 2026-11-03; issue #64). The three details marked *(builder's proposal, accepted 2026-11-03)* were proposed by the builder and accepted by the maintainer the same day. Nothing is built yet.
- **For the classroom session of 2026-11-18** (issue #69): decisions 1 and 2, and the recording part of decision 3 (`treatment.assigned` with the hand-over setting). After the class: the secret-ballot and silent-mode arms, and decision 4.
- **Supersedes in blueprint §6.2:** the visibility and fields of `prediction.answered`, and the fields of `authority.handover` (decisions 1 and 2). Adds the public event `prediction.tally`.

## Context

Four blueprint features were written for table mode, where one phone travels round the table:
- **R10:** a hand-over screen, with a spoken prediction prompt the Authority taps in (`prediction.answered`, §6.2; S6);
- **R1:** a treatment arm recorded before season 1 (`treatment.assigned`, §6.2);
- **the §5.0 timetable:** the facilitator is the Authority in seasons 0–2, then hands over to a student (`authority.handover`, §6.2);
- **E7:** a service worker for offline use.

Fairflow v1.0 is room mode (ADR 0005). Every player has a phone, the private turn is simultaneous, and the classroom session of 2026-11-18 runs several tables at once with one facilitator. The blueprint does not say what is predicted. Handoff §9 item 5 parked all four features for a design session, which the maintainer held on 2026-10-29 and completed on 2026-11-03.

## Decision

### 1. Prediction guesses (R10, `prediction.answered`)

- **Who and when.** In room mode, each irrigation scheme's player answers on their own phone at the start of the private turn. Room mode has no hand-over screen.
- **What is predicted:** the total pumped by the table this season.
- **The answer is relative and easy**, so nobody needs to know amounts: *more than last season*, *about the same* or *less than last season*.
  - **Season 1** compares with the practice round (season 0), which every table plays.
  - An exact number is optional and may be added later. The relative answer is what the debrief uses.
- **It never blocks the turn.** A player who does not answer still commits. The 45 s private-turn timer (ADR 0013) is unchanged, and an unanswered prompt records nothing.
- **What is compared (builder's proposal, accepted 2026-11-03).** The outcome uses only what the table already sees, the observed total `pumpsTotalObserved` (ADR 0004, amended 2026-10-11): *more* when this season's observed total is above last season's (or the practice round's), *less* when below, *about the same* when equal. No sealed value is used, so the comparison reveals nothing new.
- **Visibility (builder's proposal, accepted 2026-11-03).** `prediction.answered {role, metric: "pumpsTotalObserved", answer}` is visible to the predictor only (`self`), so a guess cannot steer the others. This replaces §6.2's public event with `predictedValue` and `actualValue`. At `debrief.opened` the engine writes one public `prediction.tally {season, more, same, less, outcome}` per season. It holds the counts of each answer and the outcome on the observed total, so the table sees them whichever debrief it chooses. Individual answers open to the table only with the per-player debrief (R19, `debrief.opened {perPlayer: true}`).

### 2. The Authority (`authority.handover`)

- **With several tables, each table's Authority is a student from season 0.** One facilitator cannot be the Authority in several rooms at once. The facilitator moves between tables with the printed script and the projector views. This replaces, for room mode, the facilitator as the first Authority in R3 and in §5.0 ("Authority hand-over after season 2").
- **The hand-over is a room setting**, `authorityHandoverSeason`. After that season the Authority role passes to another student's phone. **0 means never.** The default is after season 2, as in §5.0; the facilitator sets 0 for a table with no further student.
  - **The choices end at the season before the shortest game's last** (maintainer's question, answered as best practice on 2026-11-04). The game's length is drawn and kept secret (R20), so a later season can be the last: the hand-over would then happen in some games and not in others, and the record would claim an arm the game did not have. Every season a room may choose is therefore followed by a season in every game it can draw.
  - **Tables of four to six** (maintainer, 2026-11-04). With four students the table has no one to take over, and the facilitator chooses never. The Authority can always keep the role by opening the next season, so a hand-over setting with nobody to take over does no harm; the record then holds `treatment.assigned` without an `authority.handover`, which the analysis reads as "not handed over".
- **One Authority link at a time.** The server keeps one live link per role, and a newer link replaces the older. The host page holds one Authority link, which the hand-over prompt and the "Move a role" panel both show, so no screen shows a replaced code (maintainer's question, 2026-11-04).
- **The mechanism (builder's proposal, accepted 2026-11-03)** is the one seat transfer needs (issue #9): the room's host page shows a one-time transfer link for a role; opening it on the new phone moves the role there and revokes the old phone's token. The engine records `authority.handover {season, fromDevice, toDevice}`, with the salted device hashes, never names. This replaces §6.2's `from, to, season`, so that it is clear the two ends are devices: the role stays the Authority. Seat transfer for an irrigation scheme uses the same link and is recorded the same way, under its own event type.

### 3. `treatment.assigned` (R1)

- **Recorded in every game before season 1**, with all arms off as the control. The facilitator sets the arms when creating the room (`assignedBy: "facilitator"`). Seeded random assignment is added only once research mode is enabled with approval (ADR 0011).
- **The first arm variables:** `authorityHandoverSeason`, `secretBallot` and `silentMode`. The universalisation nudge and deliberation (both in §6.2's field list) come later.
- **Every record names its conditions, the fixed ones too** (maintainer's question, answered as best practice on 2026-11-04). `deliberation` holds the scenario's `session.deliberation`, which is `"table"` (the players talk face to face at one table) in every room-mode game today. Recording a condition that does not vary yet keeps each record self-describing, so records from before and after a deliberation arm can be pooled without guessing. When the deliberation arm is built, it sets this field; it does not add a new one.
- **For the class on 2026-11-18** the arm records the hand-over setting, with the secret ballot and silent mode off. Building those two arms comes after the class.

### 4. The service worker (E7)

Built together with table mode (issue #57), when offline play exists. Room mode has none before then, so a phone cannot keep a stale app version in the middle of a session.

## Consequences

- New events: `prediction.answered` (self), `prediction.tally` (public, at the debrief), `authority.handover` (public), `treatment.assigned` (public), and one event for seat transfer. They leave the §6.2 "Not yet emitted" list through the generated table when they are built.
- **The regression guard (#49) will change, intentionally.** `treatment.assigned` in every game adds an event to each Kelvara record, so the guard's fixtures are regenerated in that PR and the PR says why. No basin result changes.
- **Build order for the class:**
  1. the transfer link (#9);
  2. the Authority hand-over;
  3. predictions (private turn, then debrief);
  4. `treatment.assigned` with the hand-over setting.

  If the hand-over is not solid by the code freeze in the classroom plan (#69, 2026-11-15/16), the class runs with `authorityHandoverSeason = 0`, which the setting already allows.

## Sources

- Blueprint R1, R3, R10, R19, §5.0 (timetable), §6.2 (`prediction.answered`, `authority.handover`, `treatment.assigned`), S6, E7.
- ADR 0004 (observed total), ADR 0005 (room mode), ADR 0011 (consent and research mode), ADR 0013 (private-turn timer).
- Issue #9 (seat transfer), issue #57 (table mode), issue #64 (the design answers), issue #69 (the classroom plan).
