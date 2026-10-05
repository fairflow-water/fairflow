#!/usr/bin/env node
// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
//
// `fairflow-engine serve` — the NDJSON worker of blueprint §7.2. The only engine file that touches Node I/O.

import { readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import type { Readable, Writable } from 'node:stream';
import { pathToFileURL } from 'node:url';
import { createServeState, handleLine } from './serve.js';

/** Read NDJSON from `input`, write one reply line per non-empty input line, in order. Resolves when input ends. */
export async function runServe(input: Readable, output: Writable, engineVersion: string): Promise<void> {
  const state = createServeState(engineVersion);
  for await (const line of createInterface({ input, crlfDelay: Infinity })) {
    if (line.trim() === '') continue;
    output.write(JSON.stringify(handleLine(state, line)) + '\n');
  }
}

const isMain = process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  const [cmd] = process.argv.slice(2);
  if (cmd !== 'serve') {
    process.stderr.write('usage: fairflow-engine serve   (NDJSON commands on stdin, replies on stdout)\n');
    process.exit(2);
  }
  const { version } = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')) as { version: string };
  await runServe(process.stdin, process.stdout, version);
}
