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
FAIRFLOW_ALLOWED_ORIGINS=http://localhost:5173 uv run uvicorn fairflow_server.app:create_app --factory --no-access-log --port 8000
```

`FAIRFLOW_ALLOWED_ORIGINS` lists the browser origins allowed to open a WebSocket (comma-separated); unset, none is.

`FAIRFLOW_RESEARCH_ENABLED=1` asks every farm, at join, whether its table's record may be used for research (ADR 0011).
Leave it unset (course-only) until the placeholders in `content/information-sheet.json` are filled and ethics approval
is given. `--no-access-log` keeps client IP addresses out of uvicorn's log; configure any reverse proxy in front of the
server the same way, or keep the information sheet's sentence on IP logging and state its retention period.
