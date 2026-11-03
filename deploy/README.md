<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Deploying Fairflow on one server

One Linux VM in the EU runs two containers:
- `app`: the room server and the Python engine;
- `web`: Caddy, which serves HTTPS and the built client, and passes `/rooms` to `app`.

CI builds both images and serves a room through them on every change (the `deploy-image` job in `.github/workflows/compliance.yml`).

## What you need

- **A VM in the EU** (ADR 0011 and the information sheet), with Docker Engine and the Compose plugin. Ports 80 and 443 must be open to the internet; Caddy obtains the certificate on port 80.
- **A domain name, e.g. `fairflow.example.org`,** whose DNS A (and AAAA) record points to the VM.
- **An encrypted disk**, and **no backup of the `rooms` volume**: the store holds game records, and the information sheet promises they are deleted 24 h after the last move (ADR 0012, `packages/server/README.md`).

## First start

```sh
git clone https://github.com/fairflow-water/fairflow.git && cd fairflow
export FAIRFLOW_DOMAIN=fairflow.example.org
docker compose -f deploy/compose.yaml up -d --build
```

Open `https://fairflow.example.org`. The start page creates a room. For several tables, create one room per table; each room has its own join QR code and projector link.

## Settings

- **`FAIRFLOW_DOMAIN`** is the public name. It sets the HTTPS certificate and the one origin allowed to open a game connection.
- **Research stays off.** Do not set `FAIRFLOW_RESEARCH_ENABLED` until the consent text is complete and ethics approval is given (ADR 0011).
- **`FAIRFLOW_ROOM_TTL_HOURS`** stays at its default of 24 h (ADR 0012).
- **One server process only:** a room's lock and live connections are in memory. Do not scale `app` to more than one container.

## IP addresses

The information sheet does not mention an IP log, so none is kept:
- **Caddy** writes no access log, and its error logger, which would record the client's address on a proxy error, is excluded (`deploy/Caddyfile`);
- **the server** runs with `--no-access-log --log-level warning` and blanks the WebSocket client address (`packages/server/README.md`).

The CI job makes a WebSocket handshake and a proxy error (with the app stopped) and fails if a private or loopback address then appears in either container's log. Do not add a proxy or a load balancer in front of `web` that logs addresses. If one is required, the information sheet must say so.

## Checks after a deploy

```sh
docker compose -f deploy/compose.yaml ps            # both containers "running"
docker compose -f deploy/compose.yaml logs --tail=50 # no client addresses
```

Then play a short game with two phones and the projector link.

## Updating

**Update only between sessions:** a running game draws its deck again from the stored nonce, and a different NumPy sets unfinished rooms aside (`packages/server/README.md`).

```sh
git pull
docker compose -f deploy/compose.yaml up -d --build
```

## Stopping and removing

- `docker compose -f deploy/compose.yaml down` stops the containers; the room store and the certificates stay.
- Adding `-v` also deletes the volumes, so every room is gone.
