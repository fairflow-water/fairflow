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

## Decision (as built in the draft)

1. **A page with no room, `/pre`.** The link sent the day before opens it on the player's own phone. It shows the recipe for the code (`content/linking-code.json`, working wording from the blueprint's example) and keeps the normalised code on that phone, in local storage. Nothing is sent anywhere, because no room exists yet.
2. **The code goes with the join.** On the day, `/join/{code}` on the same phone shows the kept code and sends it with the join. The join screen still asks for nothing typed, so no name can be entered there.
3. **The record.**
   - The engine's `join` takes an optional `linkingCode`, from irrigation schemes only (`no_linking_code` for the Authority).
   - The code is capitals and digits, 1 to `LINKING_CODE_MAX` characters (`bad_linking_code`). That bound is an input bound shared with the phone (`content/linking-code.json` `maxLength`), and a test keeps the two equal.
   - The engine writes `linking.code {role, code}` with visibility `self` right after `player.joined`, so only that scheme's own projection carries it. `player.joined` is unchanged.
   - A join without a code writes no `linking.code` event. Old records replay unchanged.
4. **The paper fallback** is the same page on arrival: the player makes the code on their own phone before joining.
5. **Not built, waiting for the survey instruments (`content/surveys/`):**
   - the pre-survey itself;
   - `presurveyComplete`, which stays false;
   - R3's "nobody sees a role card before the pre-survey closes";
   - `surveys.csv`.
   The page shows a placeholder where the pre-survey will go.

## Questions for the maintainer

1. **Consent's place.** S2 puts the information sheet and two-part consent on the pre-session page, the day before. As built, consent stays at the join (ADR 0011), and the consent text and its flow are untouched. Should consent move to `/pre`? If so, the join would have to carry the consent made the day before, and ADR 0011 would change.
2. **Required or optional.** As built, a scheme may join without a code. Should a code be required whenever research is enabled, or always?
3. **Duplicate codes in one room** are accepted. Refusing a duplicate would tell a player that someone else at the table chose the same code. Is accepting them right?
4. **"Role assignment by linking code"** (S2) is a table-mode step. In room mode each player picks a free scheme on their own phone, as before. Is that reading right?
5. **The recipe.** The working wording uses the blueprint's example (mother's initials plus birth month). Does the domain lead keep that, with the instruments?

## Consequences

- One more event type, `linking.code` (self). The §6.2 table already lists it. The generated table in draft PR #29 would gain its row when both are merged.
- The phone keeps the code in local storage across sessions, so the delayed post-test can reuse it. A shared or borrowed phone would keep it too; the page says to bring "this phone".
- Research export (§6.3), with hashing by a per-cohort salt, is still not built.

## Sources

- Blueprint R3, S2 (§5.2), §5.0 (timetable, "before"), §6.2 (`linking.code`), §6.3 (`surveys.csv`, hashing), §7.3 (minimal data).
- ADR 0005 (room mode), ADR 0011 (two-part consent), ADR 0012 (persistent rooms, 24 h).
