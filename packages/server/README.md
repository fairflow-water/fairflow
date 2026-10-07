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
uv run uvicorn fairflow_server.app:create_app --factory --port 8000
```
