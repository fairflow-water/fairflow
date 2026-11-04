<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Facilitator script (draft for the maintainer and the domain lead)

The printed script for one 120-minute session in **room mode with several tables** (blueprint §5.0 timetable, §5.3 debrief; ADR 0018). **DRAFT:** the builder wrote it from the blueprint, the ADRs and the current build. The wording of the spoken lines, the examples and the debrief questions are the domain lead's content (E9). Lines in *[brackets]* are still to be written. Times are the §5.0 timetable's. Print one copy per facilitator.

## Before the day

- Check the game opens at the session's address on a phone and on the projector laptop.
- One table is one room: four to six students. Three play the irrigation schemes (the upstream citrus estate, the midstream rice cooperative, the tail-end wheat scheme), one plays the **Authority** (ADR 0018), and a fifth or sixth student helps (see minute 0–05). Each table needs a shared screen: a projector, a TV or a laptop turned to the table.
- Research is off for this session: check that the server does not set `FAIRFLOW_RESEARCH_ENABLED` (`deploy/README.md`). Students then give only part 1 of the consent (taking part) when they join (ADR 0011).
- Have one deliberation sheet per table, with the task printed (see minute 105).

## 0–05 Arrival and table formation (facilitator)

- Form tables of four to six, and name one Authority per table. Every irrigation scheme needs a player before the practice round can start, so a table needs at least four.
  - **Four students:** three schemes and the Authority. Nobody is free to take over.
  - **Five students:** the fifth is the next Authority. They sit beside the Authority and watch until the hand-over.
  - **Six students:** as for five, and the sixth shares a scheme's phone with its player; the two decide together.
  - **Three students left over:** add them, one each, to tables of four or five.
- **The Authority** opens the game's address. Under **Pass the Authority role to another student**, they choose when the role passes on (ADR 0018): **After season 2** (the default, as in §5.0) when the table has a fifth student to take over, or **Never** at a table of four. If they forget, nothing breaks: at the hand-over, the Authority keeps the role by opening the next season. Then they tap **Open a room**. Their device now holds the Authority role and shows the room's QR code and the link **Open the projector view**.
- The Authority opens the projector view on the table's shared screen.
- **The three scheme players** scan the QR code, read the information shown, tick that they will take part, and pick a free irrigation scheme.
- Say: "Keep Fairflow open with your screen on until you have sent the review form. If your screen dims or locks during the game (for example on iPhones before iOS 16.4), turn off Low Power Mode and set Auto-Lock to Never for this session, then set it back afterwards." (Blueprint §5.4: Wake Lock needs iOS 16.4+; older iOS falls back to this reminder.)

## 05–15 Season 0, the practice round (facilitator, at each table in turn)

- The Authority starts the practice round. It uses two lenses only, is not scored, and pumping costs nothing.
- Each scheme player reads their role card aloud.
- Walk the table through one full loop: negotiate, then vote, then the private turn, then the reveal.
- *[A two-sentence explanation of a "lens", in the domain lead's words.]*

## 15–80 Seasons 1 to T (the tables play)

- The game lasts 5 or 6 seasons; nobody knows which until the end.
- **Negotiation:** 3 minutes in the practice round and seasons 1 and 2, then 4 minutes. The timer runs on the server. At expiry, the previous season's lens applies.
- **The private turn:** 45 seconds on each phone. An untouched turn commits "no pumping, no action", with 3 seconds to undo.
- **The Authority's single veto per game** is on their phone during the vote.
- *[When built (ADR 0018): at the start of each private turn, every scheme player guesses whether the table will pump more, about the same or less than last season. Nobody else sees the guess until the debrief.]*
- **Moving a role** (ADR 0018): on the Authority's device, **Move a role to another phone** shows a one-time QR code for any irrigation scheme, or **Pass the Authority role**. The new phone scans it and plays on; the old phone says the role has moved. Use it when a phone fails.
- **The hand-over** (ADR 0018): at the reveal of the chosen season, the Authority's device shows **Pass the Authority role**. The Authority taps **Show the code for the next Authority**; the next student scans it, taps **Continue room**, and opens the next season. To keep the role on the same device, the Authority opens the next season instead.
- **Your job:** move between tables, answer rule questions, and never comment on anyone's choices.
- **Minute 80:** if a table is still playing, its Authority taps **End the game after this season** (during a season) or **End the game here** (at a reveal), and confirms. During a season, every device then shows that the game ends after this season; at a reveal, the game ends at once. Either way it ends validly and reveals its length (the time-box, R20).

## 80–85 Reveal and decompress (facilitator)

- The projector shows the end of the game: the game length and the scoreboard. *[Showing the deck order with its hash proof is not built yet (v1.1).]*
- At each table, read aloud the engine's debrief brief, shown on the **Authority's phone** (not on the projector): the heaviest pumping season, the lens by season with the number of changes, and the floor votes held. *[The blueprint's third line, verdict mismatches, is not in the brief yet; the two-line verdict is on the debrief screen.]*
- **Before anyone's pumping is shown**, say: "The rules made pumping rational; we debrief the rules, not the person." (blueprint §5.3; the Authority's phone shows it as "Say first".)
- Each table chooses whether to open the per-player figures (R19). If it does not, only the totals are shown.

## 85–105 Hot debrief (facilitator, Lederman's phases)

- **Describe (5 min):** what happened at your table? *[When built: the guesses each season next to what happened.]*
- **Analyse (10 min):**
  - over the replay on the projector, flip the equalisandum once;
  - flip F between consumed and diverted once if Drip was played;
  - look at the dry-season case;
  - compare the lens voted with the lens the outcome best satisfied (the two-line verdict);
  - ask one question: who decided, and whose claims counted?
- **Generalise (5 min):** *[Balotra and Mwea: two short real cases, in the domain lead's words, labelled as real examples.]*

**Branches** (blueprint §5.3), each with a time-box:
- *[no dry season]*
- *[one dominant voter]*
- *[pumping from season 1]*
- *[the game was time-boxed]*
- The blueprint's branch "facilitator played the Authority" does not apply when a student is the Authority (ADR 0018).

## 105–120 Table deliberation (the tables)

- **The task, one sheet per table:** "Write the one rule you would add before season 1, who enforces it, and what it costs."
- Each table reads its rule aloud, one minute each.
- Collect the sheets. Keying the rules into the record (`debrief.note`) is not built yet, so keep the paper.

## After the session

- The review form and its six written prompts are homework. The delayed post-test and the cold debrief come at the two-week review.
- Rooms and their records are deleted automatically 24 hours after the last move (ADR 0012).
