<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0012: Persistent rooms, deleted 24 hours after the last move

- Status: **proposed** in a draft pull request. On 2026-10-12 the maintainer chose this variant ("records kept only until the game ends plus 24 hours, on a self-hosted EU server") over keeping records for later analysis. That second variant is planned in `docs/plans/research-retention.md` and is not built.
- Builds on ADR 0011 (course-only mode, the information sheet) and on the client reconnection of review E7. The host and the country are left to the maintainer and the institute (blueprint §12.3; `[INSTITUTE]` and `[EU COUNTRY]` in the sheet).

## Context

Rooms lived only in the server's memory. A restart, a deploy or a crash ended every game in progress. The phones reconnected and then reported the room as gone. A facilitator who reloaded the page lost control of the room, because the facilitator's token was held only in the page.

Keeping rooms on disk means keeping game records on a server. The record holds no names. It does hold:

- each scheme's moves with wall-clock times;
- typed review answers;
- the room code.

With the seating the facilitator knows, or the room code, scheme and date a player keeps, these can be linked to a person (ADR 0011 context, point 3). The record is therefore personal data, and it should be kept no longer than the game needs.

## Decision

1. **A store on the server's own disk.**
   - The store is one SQLite file (`FAIRFLOW_STORE`).
   - Each accepted intent is written, in one transaction, before any client hears of it. If the write fails, the move is undone in memory as well and the client is told (`storage_failed`).
   - Unset, rooms stay in memory, for development and tests.
2. **What the store holds per room:**
   - the scenario it was opened on;
   - the game's secret nonce, from which T and the deck are drawn again;
   - the record's events;
   - the time of the last event;
   - the SHA-256 of each role token. The tokens themselves stay on the devices and are never written.
3. **Deleted 24 hours after the last event**, whether or not the game ended.
   - The period is `FAIRFLOW_ROOM_TTL_HOURS`, default 24.
   - A room past it is refused at once and is deleted by a sweep every 10 minutes. Its open connections are closed with 1008, and the phones say the room is gone.
   - SQLite runs with `secure_delete` and a rollback journal, so deleted rows are overwritten in the file.
   - The information sheet states the same period (`roomTtlHours` and the text). The server refuses to start if they differ.
4. **A restart resumes every room whose record checks out:**
   - events numbered 1..n from `game.created`;
   - the nonce reproduces the committed length and deck;
   - the engine recomputes every season (`audit`).

   A room that fails these checks is logged and not served, and it is deleted with the rest. An upgrade of NumPy changes the draw from the nonce, so it sets every unfinished room aside. Upgrade between sessions.
5. **Course-only.** With a store, the server refuses to start in research mode, because nothing is kept long enough to export.
6. **The facilitator's device keeps the facilitator's tokens.** The start page offers "Continue room X" for rooms this browser opened. A reload, or a game continued on a later day within the period, takes the room up again.

## Consequences

**Pausing.** A game can be paused and continued while the gap since the last move is shorter than the period. With 24 hours, a game stopped in the afternoon can be continued the next morning. A weekly class would need about 192 hours, and the sheet's text must then say so. Players must return on the same phone and browser, without a private window and without having pressed "Leave". A seat cannot yet move to another phone.

**Operations, outside the code** (documented in `packages/server/README.md` and the handoff):
- exclude the store's directory from backups, or the backups keep records longer than the sheet says;
- put the disk under encryption;
- set the file to owner-only;
- configure any reverse proxy in front of the server to log no client IP addresses. The sheet no longer mentions an IP log.

**A correction to ADR 0011, point 5.** `--no-access-log` does not keep client IP addresses out of uvicorn's log. uvicorn still logs each WebSocket handshake as `<ip:port> - "WebSocket /rooms/…/ws" [accepted]`, at INFO. This was seen in the Playwright run while building this record. Behind a local proxy, uvicorn's default proxy-header handling makes that the player's own address. The server now blanks the address in those lines itself (`NoClientAddress`, tested), and the documented command adds `--log-level warning`.

**Not covered.** The facilitator's saved debrief view is a file on the facilitator's own device and is not deleted by the server. The sheet says it shows schemes, never names.

## Sources

- Regulation (EU) 2016/679 (GDPR), Art. 5(1)(c) and (e) (data minimisation, storage limitation), Art. 25 (data protection by design and by default), Art. 32 (security of processing). https://eur-lex.europa.eu/eli/reg/2016/679/oj
- SQLite documentation, `PRAGMA secure_delete`. https://www.sqlite.org/pragma.html#pragma_secure_delete
