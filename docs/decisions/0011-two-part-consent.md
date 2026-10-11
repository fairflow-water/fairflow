<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0011: Two-part consent, a private research answer, and a course-only mode

- Status: **accepted** 2026-10-11 by the maintainer ("proceed on the recommendation"; the institute's own text is left as placeholders), after an independent data-protection and research-ethics review. The legal basis, controller, data protection officer, ethics reference, retention and withdrawal date are **not** decided here; they are placeholders in `content/information-sheet.json` for the maintainer and the institute to fill.
- Amends §6.2 (`player.joined`, a new `research.consent` event and visibility class), §6.3 and §10.4 of the blueprint, and review finding D6.

## Context

The join screen said "The game records your farm, your decisions and a random code for this device. It does not ask for your name." and offered one checkbox, "I agree to take part". The review found:

1. **One box for two things.** Playing is part of a course; contributing to research is a separate choice. GDPR Art. 7(2) asks that a consent request be clearly distinguishable from other matters, and the Dutch Code of Ethics for Research in the Social and Behavioural Sciences (2025, E1) asks for active opt-in. The box offered no "no", and the client always sent `consentGiven: true`.
2. **The answer was public.** `player.joined` is a public event, so every screen and every export showed who had agreed. A student's research choice should not be visible to the table or to the facilitator who grades them (ethics code H4, people in a dependent position).
3. **The text was incomplete and partly wrong.** It left out timestamps, typed review answers and the server's access log; the "random code for this device" is new at every join; and a record without names is still personal data (pseudonymous, GDPR Art. 4(5)), not anonymous.
4. **No course-only mode**, although §10.4 says the first cohort is course-only unless ethics approval arrives.

## Decision

1. **Two parts, recorded separately.**
   - *Part 1, taking part:* "I have read the information and I will take part in the game." Required to join. It is an acknowledgement of the information, not the legal basis of any processing. `player.joined` records `participationAcknowledged` and `infoSheetVersion` (the version of `content/information-sheet.json` the player was shown, so it can be shown later what each person read; Art. 7(1), ethics code E6). The server refuses a join whose sheet version is not the one it serves.
   - *Part 2, research:* "May your table's game record, without your name, be used for research?" Yes / No, nothing pre-selected, both equally easy, and joining does not depend on the answer.
2. **The research answer is never shown.** It is a separate event, `research.consent {role, researchConsent}`, with a new visibility class, `server`: no projection returns it — not to the player, the table, the display or the facilitator, and not after the debrief. It is written for every scheme join while research is enabled, whatever the answer, so its presence says nothing. Eligibility of a table (every seat said yes) is worked out only at research export on the server, after grading; that export is Tier 3 work and is not built.
3. **Course-only mode.** A deployment setting, `FAIRFLOW_RESEARCH_ENABLED` (off unless set to `1`), is recorded in `game.created` as `researchEnabled`. While it is off, the join screen shows no research paragraph and no part 2, and the engine refuses a research answer; while it is on, the engine requires one from every farm. The facilitator joins as the Authority with part 1 only: the facilitator is not a research participant.
4. **Withdrawal.** While research is enabled, the join screen and the end of the game show the room code, farm and date, "keep this if you want to withdraw"; withdrawal is possible until the date in the sheet, when the link between a seat and a person is destroyed.
5. **Less on the device and in the logs.** A "Leave this game" button at the end clears this device's role token and review drafts. The documented server commands run uvicorn with `--no-access-log`, so client IP addresses are not logged by the application server (a reverse proxy in front of it must be configured the same way; the sheet keeps a placeholder sentence for the case where it is not). The application's own log lines already carry room, role and intent type only.
6. **Words.** The review screen asks players not to type names or personal details. The debrief export is labelled for what it is — this screen's view of the record — since no screen exports the full record. "Anonymised" becomes "pseudonymised (without names)" where it described the record; "anonymisation review" stays where it names the later review that aims at anonymity.

## Consequences

- Engine: `join(deviceHash, participationAcknowledged, researchConsent, infoSheetVersion, presurveyComplete)`; `Game.create(..., researchEnabled=False)`; the `server` visibility; tests that no viewer's projection contains the research answer, that the answer is required or refused by mode, and that part 1 is required. Records made before this ADR carry `consentGiven` and replay unchanged.
- Server: the setting, the join request fields, the sheet-version check, `researchEnabled` in the room information.
- UI: S2 in the order information → part 1 → part 2 (if enabled) → farm; the withdrawal note; the leave button; the review hint; the export label.
- Content: `content/information-sheet.json`, a draft with bracketed placeholders. **Until the placeholders are filled and ethics approval is given, run with research disabled.**
- Still to build (not part of this ADR): the pre-session survey and linking code (R3), a free-text filter before research export, persistence and EU hosting (Tier 3), the research export itself.

## Sources

- Regulation (EU) 2016/679 (GDPR), Art. 4(5), 7, 89(1); Recital 33. https://eur-lex.europa.eu/eli/reg/2016/679/oj
- Deans of Social Sciences (2025). *Code of Ethics for Research in the Social and Behavioural Sciences Involving Human Participants*, revised 9 April 2025: D1, D5, E1, E6, H4.
- KNAW, NFU, NWO, TO2-federatie, Vereniging Hogescholen, VSNU (2018). *Netherlands Code of Conduct for Research Integrity*. doi:10.17026/dans-2cj-nvwu
