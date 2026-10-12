<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# fairflow-server

Room mode (ADR 0002): a facilitator opens a room, participants join by QR on a phone or laptop, and the Python engine
resolves every season on the server, which alone holds sealed data until the debrief.

```sh
uv sync --locked
uv run pytest
FAIRFLOW_ALLOWED_ORIGINS=http://localhost:5173 uv run uvicorn fairflow_server.app:create_app --factory --no-access-log --log-level warning --port 8000
```

`FAIRFLOW_ALLOWED_ORIGINS` lists the browser origins allowed to open a WebSocket (comma-separated); unset, none is.

`FAIRFLOW_RESEARCH_ENABLED=1` asks every scheme, at join, whether its table's record may be used for research (ADR 0011).
Leave it unset (course-only) until the placeholders in `content/information-sheet.json` are filled and ethics approval
is given. The server refuses research mode when a store is set (below): nothing would be kept long enough to export.

`FAIRFLOW_STORE` is the path of the room store, one SQLite file (ADR 0012). With it, a restart resumes every game;
unset, rooms live in memory only. `FAIRFLOW_ROOM_TTL_HOURS` (default 24) is how long a room is kept after its last
move; the information sheet must state the same period (`roomTtlHours` and its text), or the server will not start.

Deploying with a store:
- put the store on the server's own disk, under disk encryption; the file is created owner-only;
- **exclude the store's directory from backups**, or the backups keep records longer than the sheet promises;
- upgrade NumPy only between sessions: the deck is drawn again from the stored nonce, and a different NumPy sets
  unfinished rooms aside.

**IP addresses.** `--no-access-log` stops uvicorn's HTTP access log, but uvicorn still logs each WebSocket handshake
with the client's address; the server blanks that address itself (`NoClientAddress` in `app.py`), and
`--log-level warning` drops those lines altogether. The information sheet says nothing
about an IP log, so **any reverse proxy in front of the server must be configured to log no client IP addresses** (for
nginx, an `access_log off;` or a `log_format` without `$remote_addr` and `$http_x_forwarded_for`). If that cannot be
done, the sheet must say so again, with how long the log is kept.
