// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Real-browser end-to-end test: the Python room server and the production client build (served by `vite preview`,
// which proxies /rooms to the server so page and server share one origin, as in deployment).
import { defineConfig, devices } from '@playwright/test';

const CLIENT = 'http://localhost:4173';

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
      command: 'uv run uvicorn fairflow_server.app:create_app --factory --port 8000',
      cwd: '../server',
      url: 'http://localhost:8000/openapi.json',
      env: { FAIRFLOW_ALLOWED_ORIGINS: CLIENT },
      reuseExistingServer: !process.env['CI'],
      timeout: 120_000,
    },
    {
      command: 'npx vite build && npx vite preview --port 4173 --strictPort',
      url: CLIENT,
      reuseExistingServer: !process.env['CI'],
      timeout: 120_000,
    },
  ],
});
