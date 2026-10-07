// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// In development the room server runs on :8000; Vite proxies REST and the WebSocket so the page and the server share
// one origin, as they will in production behind one host.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/rooms': { target: 'http://localhost:8000', ws: true } } },
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/main.tsx'],
      thresholds: { lines: 80, branches: 70, functions: 75, statements: 80 },
    },
  },
});
