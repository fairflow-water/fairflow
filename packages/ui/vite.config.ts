// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
import { readFileSync } from 'node:fs';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// ADR 0018: the start page offers the hand-over season. Only the two values it needs are read from the shipped scenario
// here, at build time, so that no other scenario number (inflows, aquifer, goals) reaches the client bundle.
const scenario = JSON.parse(readFileSync(new URL('../scenarios/default-basin.json', import.meta.url), 'utf-8')) as {
  treatments: { authorityHandoverSeason: number }; basin: { gameLength: { min: number } };
};
const roomSettings = {
  authorityHandoverSeason: scenario.treatments.authorityHandoverSeason,
  shortestGame: scenario.basin.gameLength.min,
};

// In development the room server runs on :8000; Vite proxies REST and the WebSocket so the page and the server share
// one origin, as they will in production behind one host. `vite preview` (the end-to-end test) proxies the same way.
// FAIRFLOW_SERVER_URL points the proxy elsewhere (the end-to-end test runs its own server on a port of its own).
const proxy = { '/rooms': { target: process.env['FAIRFLOW_SERVER_URL'] ?? 'http://localhost:8000', ws: true } };

export default defineConfig({
  plugins: [react()],
  define: { __ROOM_SETTINGS__: JSON.stringify(roomSettings) },
  server: { proxy },
  preview: { proxy },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/main.tsx'],
      thresholds: { lines: 80, branches: 70, functions: 75, statements: 80 },
    },
  },
});
