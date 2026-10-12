<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Plan, not built: records kept for later analysis

The other variant of the persistent-rooms decision (ADR 0012), written on 2026-10-12. It is **not built**. Building it needs:

- the maintainer's decisions listed at the end;
- ethics approval;
- a decision record that amends ADR 0011 and ADR 0012.

## Shape

The live store of ADR 0012 stays as it is. Behind it, a record passes through three stages.

1. **Live store** (ADR 0012), on the self-hosted EU server.
   - At last event + 24 hours, the tokens are deleted.
   - For a course-only room, everything is deleted, as today.
   - For a research room, the record moves to the pending store.
2. **Pending store, until a research export date after grading.** ADR 0011 says eligibility is worked out only "after grading".
   - `fairflow-admin export --after <date>` keeps a table only if every scheme answered yes, as the sheet promises.
   - After the export, every pending record is deleted, whether exported or not.
3. **Research archive**, one entry per eligible table:
   - a random archive ID in place of the room code;
   - times as seconds since `game.created`, not wall-clock times;
   - no `deviceId`, no `research.consent` (every answer was yes) and a single `infoSheetVersion`;
   - review text flagged for a person to check and clean before any use. The sheet already says "typed answers are checked".

   Deleted after `FAIRFLOW_ARCHIVE_RETENTION_DAYS`.

**Withdrawal.**
- A separate key table maps room code + date to archive ID.
- `fairflow-admin withdraw <code> <date> <scheme>` deletes that table's whole record. The table is the unit, because one "no" makes a table ineligible.
- The key table is deleted after `FAIRFLOW_WITHDRAWAL_DAYS`. From then on "the record cannot be traced to you".

**Settings and checks.**
- Research mode refuses to start unless both periods are set and the sheet has no `[BRACKETED]` text left.
- The sheet holds `{archiveYears}` and `{withdrawalDays}`. The server fills them in, and the sheet version includes the values, so a join records exactly what the player read.
- ADR 0012's refusal of research mode with a store is lifted only by this plan's build.

**Tests.**
- Export eligibility: all yes is kept, one no is dropped.
- The archive holds no room code, `deviceId` or wall-clock time.
- Withdrawal deletes the table.
- The key table and the archive are deleted on schedule, using a fake clock.
- The pending store is empty after export.

**Size:** about three to four days.

## Sheet sentences this variant would use

- **"Changing your mind":** "Write to [CONTACT E-MAIL] with your room code, scheme and date within {withdrawalDays} days after today's game. After that, the record cannot be traced to you."
- **"Data protection",** in place of the 24-hour sentence: "During the game and for 24 hours after it, the record is kept on a server run by [INSTITUTE] in [EU COUNTRY]. If everyone at your table said yes to research, a copy without the room code, device codes or clock times is then kept on [RESEARCH STORAGE] for {archiveYears} years and then deleted; otherwise nothing is kept after [EXPORT DATE RULE]."
- **"What the game records"** and **"Who sees what":** as in ADR 0012.

## Decisions needed first

- Where research records are kept (`[RESEARCH STORAGE]`).
- The archive period.
- The withdrawal window.
- The export date rule (after which grading).
- Who checks the typed answers.
- Every blank that ADR 0011 left: controller, legal basis, DPO, ethics reference, contact, and course and researcher names.
