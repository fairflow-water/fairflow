// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// The process flow from the browser to the room server, route by route, in real browsers against the production
// build (same origin as in deployment: /rooms is proxied to the server). room.spec.ts, reconnect.spec.ts and
// transfer.spec.ts own the happy paths of a whole game, reconnection and moving a role; this file walks every page
// route and every server endpoint once, including how each refuses what it must refuse, and plays both branches of
// the time-box (R20) and the totals-only debrief, which no other browser test reaches. It checks wiring and refusals,
// not model numbers, which the engine tests own.
import { expect, test, type APIRequestContext, type Browser, type Page } from '@playwright/test';

const PHONE = { viewport: { width: 360, height: 640 } }; // §5.1: 360 × 640 portrait first
const DEVICE = 'flow-spec-device-0001'; // test input: a device hash for the API-level joins

async function newPage(browser: Browser, options = {}): Promise<Page> {
  return (await browser.newContext(options)).newPage();
}

async function openRoom(host: Page): Promise<string> {
  await host.goto('/');
  await host.getByRole('button', { name: 'Open a room' }).click();
  const heading = await host.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  return (heading ?? '').replace('Room ', '').trim();
}

async function joinPhone(browser: Browser, code: string): Promise<Page> {
  const phone = await newPage(browser, PHONE);
  await phone.goto(`/join/${code}`);
  await phone.getByRole('checkbox', { name: /will take part/ }).check();
  await phone.getByRole('list').getByRole('button').first().click();
  await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
  return phone;
}

async function detail(r: Awaited<ReturnType<APIRequestContext['post']>>): Promise<string | undefined> {
  return ((await r.json()) as { detail?: { code?: string } }).detail?.code;
}

interface Reply { type: string; code?: string; role?: string }
interface Talk { replies: Reply[]; close: number | null }

/** Open the room socket from the page's own (allowed) origin, send `first` and then `then`, and collect the server's
 * replies until `want` have arrived or the socket closes; never longer than 10 s, so a proxy failure fails fast. */
async function talk(page: Page, code: string, first: string, then: string[] = [], want = 1): Promise<Talk> {
  return page.evaluate(([room, firstMessage, rest, wanted]) => new Promise<Talk>(resolve => {
    const out: Talk = { replies: [], close: null };
    const ws = new WebSocket(`${location.origin.replace(/^http/, 'ws')}/rooms/${room}/ws`);
    const done = () => { resolve(out); ws.close(); };
    setTimeout(done, 10_000);
    ws.addEventListener('open', () => { ws.send(firstMessage); for (const m of rest) ws.send(m); });
    ws.addEventListener('message', e => {
      out.replies.push(JSON.parse(String(e.data)) as Reply);
      if (out.replies.length >= wanted) done();
    });
    ws.addEventListener('close', e => { out.close = e.code; resolve(out); });
    ws.addEventListener('error', () => resolve(out));
  }), [code, first, then, want] as const);
}

const auth = (t: string) => JSON.stringify({ token: t });

test('every page route and server endpoint answers as designed, refusals included', async ({ browser, request }) => {
  // ---- POST /rooms and GET /rooms/{code}
  const created = await request.post('/rooms', { data: { scenario: 'default-basin' } });
  expect(created.status()).toBe(200);
  const room = await created.json() as { room: string; facilitatorToken: string; displayToken: string; joinPath: string };
  expect(room.room).toMatch(/^[A-Z2-9]{5}$/);
  expect(room.joinPath).toBe(`/join/${room.room}`);
  const unknownScenario = await request.post('/rooms', { data: { scenario: 'no-such-basin' } });
  expect([unknownScenario.status(), await detail(unknownScenario)]).toEqual([404, 'unknown_scenario']);
  expect((await request.post('/rooms', { data: { scenario: 'default-basin', surprise: 1 } })).status()).toBe(422);

  const info = await (await request.get(`/rooms/${room.room}`)).json() as {
    freeRoles: string[]; phase: string; researchEnabled: boolean; infoSheetVersion: string; scenario: { schemes: { id: string }[] };
  };
  expect(info.phase).toBe('lobby');
  expect(info.researchEnabled).toBe(false); // course mode: S2 asks no research question
  expect(info.freeRoles).toEqual(info.scenario.schemes.map(s => s.id));
  const missing = await request.get('/rooms/ZZZZZ');
  expect([missing.status(), await detail(missing)]).toEqual([404, 'unknown_room']);

  // ---- POST /rooms/{code}/join
  const [first, second] = info.freeRoles as [string, string];
  const join = (role: string, extra: Record<string, unknown> = {}) => request.post(`/rooms/${room.room}/join`, {
    data: { role, deviceHash: DEVICE, participationAcknowledged: true, researchConsent: null,
      infoSheetVersion: info.infoSheetVersion, presurveyComplete: false, ...extra },
  });
  const joined = await join(first);
  expect(joined.status()).toBe(200);
  const firstToken = (await joined.json() as { token: string }).token;
  const again = await join(first);
  expect([again.status(), await detail(again)]).toEqual([409, 'role_unavailable']); // a seat is taken once
  const unticked = await join(second, { participationAcknowledged: false });
  expect([unticked.status(), await detail(unticked)]).toEqual([409, 'not_acknowledged']); // part 1 is required
  const stale = await join(second, { infoSheetVersion: 'an-older-sheet' });
  expect([stale.status(), await detail(stale)]).toEqual([409, 'stale_information_sheet']);
  expect((await join(second, { surprise: 1 })).status()).toBe(422); // the request model forbids extra fields
  expect((await (await request.get(`/rooms/${room.room}`)).json() as { freeRoles: string[] }).freeRoles).not.toContain(first);

  // ---- POST /rooms/{code}/transfers and /transfers/claim
  const offer = (token: string, role: string) => request.post(`/rooms/${room.room}/transfers`, { data: { token, role } });
  const byPlayer = await offer(firstToken, second);
  expect([byPlayer.status(), await detail(byPlayer)]).toEqual([409, 'not_authority']);
  const toEmptySeat = await offer(room.facilitatorToken, second);
  expect([toEmptySeat.status(), await detail(toEmptySeat)]).toEqual([409, 'not_seated']);
  const bogusClaim = await request.post(`/rooms/${room.room}/transfers/claim`, { data: { link: 'not-a-link', deviceHash: DEVICE } });
  expect([bogusClaim.status(), await detail(bogusClaim)]).toEqual([409, 'unknown_transfer']);
  const made = await offer(room.facilitatorToken, first);
  expect(made.status()).toBe(200);
  const link = (await made.json() as { link: string }).link;
  expect(link).toBeTruthy();
  // the Authority role can be passed on too (transfer.spec.ts claims one)
  expect((await offer(room.facilitatorToken, 'authority')).status()).toBe(200);

  // ---- WS /rooms/{code}/ws: a real token is welcomed and synced; the projector cannot act; a malformed intent is
  // named; a wrong token, a transfer link, an unknown room and an oversized message are each refused
  const probe = await newPage(browser);
  await probe.goto('/');
  const start = JSON.stringify({ intent: 'start_season' });
  const shown = await talk(probe, room.room, auth(room.displayToken), [start, JSON.stringify({ intent: 'no_such' })], 4);
  expect(shown.replies.map(r => r.type)).toEqual(['welcome', 'sync', 'rejected', 'invalid']);
  expect([shown.replies[0]?.role, shown.replies[2]?.code]).toEqual(['display', 'read_only']);
  expect((await (await request.get(`/rooms/${room.room}`)).json() as { phase: string }).phase).toBe('lobby');
  const refused = async (code: string, firstMessage: string) => (await talk(probe, code, firstMessage, [], 99)).close;
  expect(await refused(room.room, auth('wrong-token'))).toBe(1008);
  expect(await refused(room.room, auth(link))).toBe(1008); // a link is for claiming, never for playing
  expect(await refused('ZZZZZ', auth(room.displayToken))).toBe(1008);
  expect(await refused(room.room, 'x'.repeat(65 * 1024))).toBe(1009); // over the server's 64 KiB message cap

  // ---- page routes, each with what it must say when something is wrong
  await probe.goto('/join/ZZZZZ');
  await expect(probe.getByRole('alert')).toHaveText(/This room could not be joined \(unknown_room\)/);
  await probe.goto(`/join/${room.room.toLowerCase()}`); // a code typed in lower case still finds the room
  await expect(probe.getByRole('heading', { name: `Room ${room.room}` })).toBeVisible();
  await probe.goto(`/display/${room.room}#wrong-token`);
  await expect(probe.getByRole('alert')).toHaveText(/no longer on the server/);
  await probe.goto(`/transfer/${room.room}#not-a-link`);
  await expect(probe.getByRole('alert')).toHaveText(/This link has been used or replaced/);
  await probe.goto('/no/such/page');
  await expect(probe.getByRole('button', { name: 'Open a room' })).toBeVisible(); // anything else is the start page

  // the projector shows the room, its join QR code and the lobby, and none of the Authority's controls
  await probe.goto(`/display/${room.room}#${room.displayToken}`);
  await expect(probe.getByRole('img', { name: new RegExp(`QR code to join: .*/join/${room.room}`) })).toBeVisible();
  await expect(probe.getByText(/Waiting for the facilitator/)).toBeVisible();
  await expect(probe.getByText('Move a role to another phone')).toHaveCount(0);
  await expect(probe.getByRole('button', { name: /Start the practice round|End the game/ })).toHaveCount(0);

  // the two seats left are taken in the browser; a fourth phone is told every scheme is taken
  for (let i = 0; i < info.freeRoles.length - 1; i++) await joinPhone(browser, room.room);
  const late = await newPage(browser, PHONE);
  await late.goto(`/join/${room.room}`);
  await late.getByRole('checkbox', { name: /will take part/ }).check();
  await expect(late.getByText('Every irrigation scheme is taken.')).toBeVisible();
  expect((await (await request.get(`/rooms/${room.room}`)).json() as { freeRoles: string[] }).freeRoles).toEqual([]);
});

test('the Authority time-boxes the game (R20): every device is told, the season ends the game, the debrief opens', async ({ browser }) => {
  const host = await newPage(browser);
  const code = await openRoom(host);
  const display = await newPage(browser);
  await display.goto((await host.getByRole('link', { name: 'Open the projector view' }).getAttribute('href')) ?? '');
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) phones.push(await joinPhone(browser, code));

  // no time-box in the practice round, which is not scored
  await host.getByRole('button', { name: 'Start the practice round' }).click();
  await expect(display.getByText('Practice round (not scored)')).toBeVisible();
  await expect(host.getByText('Practice round (not scored)')).toBeVisible(); // the host is in the round, not the lobby
  await expect(host.getByRole('button', { name: /End the game/ })).toHaveCount(0);
  await host.getByTestId('lens-utilitarian').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await host.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of phones) await phone.getByRole('button', { name: 'Commit my turn' }).click();
  await host.getByRole('button', { name: 'Open season 1', exact: true }).click();

  // season 1: only the Authority sees the button; "Keep playing" changes nothing; a confirmed time-box reaches all
  for (const page of [host, display, ...phones]) await expect(page.getByText('Season 1', { exact: true })).toBeVisible();
  for (const page of [display, ...phones]) await expect(page.getByRole('button', { name: /End the game/ })).toHaveCount(0);
  await host.getByRole('button', { name: 'End the game after this season' }).click();
  await host.getByRole('button', { name: 'Keep playing' }).click();
  await expect(host.getByRole('button', { name: 'End the game after this season' })).toBeVisible();
  await host.getByRole('button', { name: 'End the game after this season' }).click();
  await host.getByRole('button', { name: 'Yes, end after this season' }).click();
  for (const page of [host, display, ...phones]) await expect(page.getByText('The game ends after this season.')).toBeVisible();
  await expect(host.getByRole('button', { name: /End the game/ })).toHaveCount(0);

  // the season is still played out, and then the game ends without a next season
  await host.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await host.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of phones) await phone.getByRole('button', { name: 'Commit my turn' }).click();
  for (const page of [host, display, ...phones]) await expect(page.getByText(/The game lasted .*\(time-boxed\)/)).toBeVisible();
  await expect(host.getByRole('button', { name: 'Open the next season' })).toHaveCount(0);
  for (const phone of phones) await expect(phone.getByText(/Your goal/)).toBeVisible();

  await host.getByRole('button', { name: /reveal who pumped/ }).click();
  for (const page of [host, display, ...phones]) await expect(page.getByRole('heading', { name: 'Debrief' })).toBeVisible();
});

test('between seasons the Authority ends the game at once (R20), and the debrief can show totals only', async ({ browser }) => {
  const host = await newPage(browser);
  const code = await openRoom(host);
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) phones.push(await joinPhone(browser, code));

  await host.getByRole('button', { name: 'Skip it and open season 1' }).click();
  await host.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await host.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of phones) await phone.getByRole('button', { name: 'Commit my turn' }).click();

  // at the reveal the button ends the game here, not after a further season
  await expect(host.getByRole('heading', { name: 'Season 1: what happened' })).toBeVisible();
  await host.getByRole('button', { name: 'End the game here' }).click();
  await host.getByRole('button', { name: 'Yes, end the game now' }).click();
  for (const page of [host, ...phones]) await expect(page.getByText(/The game lasted .*\(time-boxed\)/)).toBeVisible();
  await expect(host.getByRole('button', { name: 'Open the next season' })).toHaveCount(0);

  // totals only: every device sees the debrief, and no device sees which scheme pumped what
  await host.getByRole('button', { name: 'Open the debrief: totals only' }).click();
  for (const page of [host, ...phones]) {
    await expect(page.getByRole('heading', { name: 'Debrief' })).toBeVisible();
    await expect(page.getByTestId('sealed-note')).toBeVisible();
    await expect(page.getByRole('table', { name: /Each scheme/ })).toHaveCount(0);
  }
});
