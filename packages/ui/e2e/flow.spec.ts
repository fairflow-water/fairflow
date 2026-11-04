// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// The process flow from the browser to the room server, route by route, in real browsers against the production
// build (same origin as in deployment: /rooms is proxied to the server). room.spec.ts, reconnect.spec.ts and
// transfer.spec.ts own the happy paths of a whole game, reconnection and moving a role; this file walks every page
// route and every server endpoint once, including how each refuses what it must refuse, and plays the time-box (R20)
// that no other browser test reaches. It checks wiring and refusals, not model numbers, which the engine tests own.
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

/** The close code the room socket gives this token, opened from the page's own (allowed) origin. */
async function closeCode(page: Page, code: string, token: string): Promise<number> {
  return page.evaluate(([room, tok]) => new Promise<number>(resolve => {
    const ws = new WebSocket(`${location.origin.replace(/^http/, 'ws')}/rooms/${room}/ws`);
    ws.addEventListener('open', () => ws.send(JSON.stringify({ token: tok })));
    ws.addEventListener('close', e => resolve(e.code));
  }), [code, token] as const);
}

async function detail(r: Awaited<ReturnType<APIRequestContext['post']>>): Promise<string | undefined> {
  return ((await r.json()) as { detail?: { code?: string } }).detail?.code;
}

test('every page route and server endpoint answers as designed, refusals included', async ({ browser, request }) => {
  // ---- POST /rooms and GET /rooms/{code}
  const created = await request.post('/rooms', { data: { scenario: 'default-basin' } });
  expect(created.status()).toBe(200);
  const room = await created.json() as { room: string; facilitatorToken: string; displayToken: string; joinPath: string };
  expect(room.room).toMatch(/^[A-Z2-9]{5}$/);
  expect(room.joinPath).toBe(`/join/${room.room}`);
  const unknownScenario = await request.post('/rooms', { data: { scenario: 'no-such-basin' } });
  expect([unknownScenario.status(), await detail(unknownScenario)]).toEqual([404, 'unknown_scenario']);

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
  expect(again.status()).toBe(409); // a seat is taken once
  expect(await detail(again)).toBeTruthy();
  expect((await join(second, { participationAcknowledged: false })).status()).toBe(409); // part 1 is required
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
  const link = (await (await offer(room.facilitatorToken, first)).json() as { link: string }).link;

  // ---- WS /rooms/{code}/ws: a real token is welcomed; a wrong one, a transfer link or an unknown room is refused
  const probe = await newPage(browser);
  await probe.goto('/');
  const welcome = await probe.evaluate(([code, tok]) => new Promise<string>(resolve => {
    const ws = new WebSocket(`${location.origin.replace(/^http/, 'ws')}/rooms/${code}/ws`);
    ws.addEventListener('open', () => ws.send(JSON.stringify({ token: tok })));
    ws.addEventListener('message', e => { resolve((JSON.parse(String(e.data)) as { type: string }).type); ws.close(); });
  }), [room.room, room.displayToken] as const);
  expect(welcome).toBe('welcome');
  expect(await closeCode(probe, room.room, 'wrong-token')).toBe(1008);
  expect(await closeCode(probe, room.room, link)).toBe(1008); // a link is for claiming, never for playing
  expect(await closeCode(probe, 'ZZZZZ', room.displayToken)).toBe(1008);

  // ---- page routes, each with what it must say when something is wrong
  await probe.goto('/join/zzzzz'); // lower case is read as upper case
  await expect(probe.getByRole('alert')).toHaveText(/This room could not be joined \(unknown_room\)/);
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
  await expect(host.getByRole('button', { name: /End the game/ })).toHaveCount(0);
  await host.getByTestId('lens-utilitarian').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await host.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of phones) await phone.getByRole('button', { name: 'Commit my turn' }).click();
  await host.getByRole('button', { name: 'Open season 1', exact: true }).click();

  // season 1: only the Authority sees the button; "Keep playing" changes nothing; a confirmed time-box reaches all
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
  for (const page of [host, display, ...phones]) await expect(page.getByText(/The game lasted/)).toBeVisible();
  await expect(host.getByRole('button', { name: 'Open the next season' })).toHaveCount(0);
  for (const phone of phones) await expect(phone.getByText(/Your goal/)).toBeVisible();

  await host.getByRole('button', { name: /reveal who pumped/ }).click();
  for (const page of [host, display, ...phones]) await expect(page.getByRole('heading', { name: 'Debrief' })).toBeVisible();
});
