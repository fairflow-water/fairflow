<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0016: The pre-session flow and the personal linking code in room mode

- Status: **proposed**, in a draft pull request, for the maintainer's review.
- Implements R3's personal linking code and S2's pre-session part, up to the point where the survey instruments are needed. Adds one event type to the Season Record, `linking.code`, which blueprint §6.2 already lists.

## Context

- **R3:** "Consent, pre-survey and the personal linking code are completed before the session on the player's own phone (QR sent the day before; paper on arrival for anyone who has not). Nobody sees a role card before the pre-survey closes."
- **S2:** "On the player's own phone, the day before: the information sheet and two-part consent …, pre-survey, personal linking code (`linking.code`). On the shared phone at the table: role assignment only, by linking code". Its acceptance criterion: "`player.joined` carries part 1, the sheet version, pre-survey and code before any role is shown".
- **§6.2:** `linking.code | self | role, code (participant-generated, e.g. mother's initials + birth month)`. It "links pre-, post- and delayed-post surveys without identity; never stored with a name".
- **§6.3:** survey answers are not record events. They are rows in `surveys.csv`, keyed by linking code. Linking codes are hashed with a per-cohort salt before research export.
- **Room mode (ADR 0005, ADR 0012):** a room is opened at the session and deleted 24 h after its last move. A link sent the day before therefore cannot point at a room. S2 was written for table mode, where the shared phone joins players "by linking code".

## Decision (as built in the draft, with the maintainer's answers of 2026-10-15)

1. **A page with no room, `/pre`.** The link sent the day before opens it on the player's own phone. It shows the recipe for the code and keeps the normalised code on that phone, in local storage. Nothing is sent anywhere, because no room exists yet.
   - The recipe in `content/linking-code.json` is **placeholder wording**, from the blueprint's example. The maintainer decided that the recipe waits for the domain lead and the survey instruments, and the page shows it as a placeholder.
2. **The code goes with the join.** On the day, `/join/{code}` on the same phone shows the kept code and sends it with the join. The join screen asks for nothing typed, so no name can be entered there.
3. **Consent does not move.** It stays exactly as ADR 0011 defines it, on `/join/{code}`. Neither the consent text, nor its flow, nor its URL changes. `/pre` carries no consent.
4. **Required from every seated player while research is enabled.**
   - While research is enabled, every irrigation scheme must bring a code (`linking_code_needed`), whatever its own research answer: the requirement is per room, never only from consenting players (ADR 0011). A phone without one is sent to `/pre` before any scheme is shown.
   - In a course-only room the code is optional.
   - The Authority never gives one (`no_linking_code`).
5. **Duplicate codes are allowed, with a warning.** A code already given in the room is recorded again. The server's join reply carries `warning: duplicate_linking_code`, and the second holder's phone shows only "Choose a different code." before going on; it does not say that anyone else holds the code. The first holder and every other screen are told nothing.
6. **The record.**
   - The code is capitals and digits, 1 to `LINKING_CODE_MAX` characters (`bad_linking_code`). The bound is shared with the phone through `content/linking-code.json` `maxLength`, and a test keeps the two equal.
   - The engine writes `linking.code {role, code}` with visibility `self` right after `player.joined`, so only that scheme's own projection carries it. `player.joined` is unchanged. The maintainer kept this separate `self` event over S2's wording that `player.joined` carries the code.
   - A join without a code writes no `linking.code` event. Old records replay unchanged.
   - §6.2's generated table now lists `linking.code`, and the event has left the "Not yet emitted" list.
7. **A player without a phone** is not served here. R3's paper fallback is recorded as part of issue #9 (seat transfer): there the facilitator enters the code. A player with a phone but no code yet uses the same page on arrival.
8. **Not built, waiting for the survey instruments (`content/surveys/`):**
   - the pre-survey itself;
   - `presurveyComplete`, which stays false;
   - R3's "nobody sees a role card before the pre-survey closes";
   - `surveys.csv`.

   The page shows a placeholder where the pre-survey will go.

## The room-mode reading of "role assignment by linking code"

S2's "On the shared phone at the table: role assignment only, by linking code" describes table mode, where one phone passes round the table. In room mode the blueprint itself gives the join: **R2**, "Room mode: join by code, pick a free role." Each player therefore picks a free irrigation scheme on their own phone, after part 1 of consent, and the linking code goes with that join (decision 2). It does not assign the role.

## Maintainer's answers (2026-10-15)

- Consent stays as ADR 0011 defines it. Only the URL could move, and it does not (decision 3).
- The linking code is required only when research is enabled (decision 4).
- Duplicate codes are allowed, with a warning (decision 5).
- The room-mode reading is quoted from R2 above.
- The recipe wording waits for the domain lead and is marked as a placeholder (decision 1).

Second answers (2026-10-15), to the open questions of the first draft:

- The linking code is required from every seated player whenever research is enabled, never only from consenting players (ADR 0011) (decision 4).
- The duplicate warning says only "choose a different code" (decision 5).
- The separate `self` event stays (decision 6).
- The no-phone path is recorded as part of issue #9, where the facilitator enters the code; it is not built here (decision 7).

## Open questions

1. A duplicate is still recorded, and the player has already joined when "Choose a different code." appears. As built, the phone keeps the code it had, so the delayed post-test would see the duplicate again unless the player makes a new code on `/pre`. Should the warning clear the kept code, or link to `/pre`, or should the join itself be refused until another code is given?
2. "Every seated player" is read as every irrigation scheme. The Authority's seat is the facilitator's and still gives no code (`no_linking_code`). Is that the reading you want?

## Consequences

- One more event type, `linking.code` (self). §6.2's generated table (PR #29) carries its row, and the event has left the "Not yet emitted" list.
- The phone keeps the code in local storage across sessions, so the delayed post-test can reuse it. A shared or borrowed phone would keep it too; the page says to bring "this phone".
- Research export (§6.3), with hashing by a per-cohort salt, is still not built.

## Sources

- Blueprint R3, S2 (§5.2), §5.0 (timetable, "before"), §6.2 (`linking.code`), §6.3 (`surveys.csv`, hashing), §7.3 (minimal data).
- ADR 0005 (room mode), ADR 0011 (two-part consent), ADR 0012 (persistent rooms, 24 h).
