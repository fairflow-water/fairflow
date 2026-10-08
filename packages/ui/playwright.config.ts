// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Real-browser end-to-end test: the Python room server and the production client build (served by `vite preview`,
// which proxies /rooms to the server so page and server share one origin, as in deployment).
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Ports of the test's own servers, chosen away from the development defaults (8000, 5173) so that the test never talks
// to something else already listening there; both servers always start fresh from the working tree.
const SERVER_PORT = 8765;
const CLIENT_PORT = 4173;
const SERVER = `http://localhost:${SERVER_PORT}`;
// Vite is started by file path with this Node, not through PATH: on Windows a long PATH with stray quotes can hide
// node_modules/.bin from the shell Playwright starts. The type check runs in its own CI job, so only the build runs here.
const vite = join(dirname(createRequire(import.meta.url).resolve('vite/package.json')), 'bin', 'vite.js');
const node = `"${process.execPath}"`;
// webServer.env replaces the environment rather than extending it, so pass the current one through (PATH included).
const inherited = Object.fromEntries(Object.entries(process.env).filter((e): e is [string, string] => e[1] !== undefined));
const CLIENT = `http://localhost:${CLIENT_PORT}`;

export default defineConfig({
  testDir: 'e2e',
  timeout: 240_000, // a whole game, up to the scenario's longest length
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0, // a pass on retry is still reported as flaky
  reporter: process.env['CI'] ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: { baseURL: CLIENT, trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `uv run uvicorn fairflow_server.app:create_app --factory --port ${SERVER_PORT}`,
      cwd: '../server',
      url: `${SERVER}/openapi.json`,
      env: { ...inherited, FAIRFLOW_ALLOWED_ORIGINS: CLIENT },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `${node} "${vite}" build && ${node} "${vite}" preview --port ${CLIENT_PORT} --strictPort`,
      url: CLIENT,
      env: { ...inherited, FAIRFLOW_SERVER_URL: SERVER },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
