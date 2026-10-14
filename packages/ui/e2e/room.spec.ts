// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// A whole game in real browsers (ADR 0005): a facilitator opens a room, a projector and three phones join (each in its
// own browser context, so each holds only its own token); the table plays to the end, opens the debrief and one scheme
// answers the review form.
// It checks the wiring and what each device may see (ADR 0004), not model numbers, which the engine tests own.
import { expect, test, type Browser, type Page } from '@playwright/test';

const PHONE = { viewport: { width: 360, height: 640 } }; // §5.1: 360 × 640 portrait first

async function newPage(browser: Browser, options = {}): Promise<Page> {
  const context = await browser.newContext(options);
  return context.newPage();
}

test('a full game: open, join by link, vote, private turns, reveal, game end, debrief', async ({ browser }) => {
  const facilitator = await newPage(browser);
  await facilitator.goto('/');
  await facilitator.getByRole('button', { name: 'Open a room' }).click();
  const heading = await facilitator.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  const code = (heading ?? '').replace('Room ', '').trim();
  expect(code).toMatch(/^[A-Z2-9]{5}$/);
  await expect(facilitator.getByRole('img', { name: /QR code to join/ })).toBeVisible();

  const display = await newPage(browser);
  const displayHref = await facilitator.getByRole('link', { name: 'Open the projector view' }).getAttribute('href');
  await display.goto(displayHref ?? '');
  await expect(display.getByText(/Waiting for the facilitator/)).toBeVisible();

  // The first phone's room socket runs through a route the test can cut, as a locked phone or lost Wi-Fi would.
  // (Chromium's offline emulation does not close an open WebSocket.)
  const link: { down: boolean; cut: () => Promise<void> } = { down: false, cut: () => Promise.resolve() };
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    if (i === 0) {
      await phone.routeWebSocket(/\/rooms\/[^/]+\/ws$/, async ws => {
        if (link.down) { await ws.close({ code: 1001, reason: 'no network' }); return; }
        const server = ws.connectToServer();
        link.cut = async () => { await ws.close({ code: 1001, reason: 'no network' }); await server.close(); };
      });
    }
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /will take part/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  // R3 season 0: the practice round, two lenses, free pumping, nothing scored
  await facilitator.getByRole('button', { name: 'Start the practice round' }).click();
  await expect(display.getByText('Practice round (not scored)')).toBeVisible();
  await expect(facilitator.getByTestId('lens-egalitarian')).toHaveCount(0);
  await facilitator.getByTestId('lens-utilitarian').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await facilitator.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of phones) {
    await expect(phone.getByText(/Pump cost at today's aquifer level: 0 points/)).toBeVisible();
    await phone.getByRole('button', { name: 'Commit my turn' }).click();
  }
  await expect(display.getByRole('heading', { name: /Practice round: what happened/ })).toBeVisible();

  let open = facilitator.getByRole('button', { name: 'Open season 1', exact: true });
  for (let season = 1; ; season++) {
    await open.click();
    if (season === 2) {
      // R8 (ADR 0015): the table votes for the biggest harvest; the Authority vetoes it once, after confirming, and
      // every screen says so; the votes are cleared and the remaining lens is re-voted
      for (const lens of ['proportional', 'utilitarian', 'egalitarian']) {
        await facilitator.getByTestId(`lens-${lens}`).getByRole('button', { name: 'Propose' }).click();
      }
      for (const phone of phones) await phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }).click();
      const row = facilitator.getByTestId('lens-utilitarian');
      await row.getByRole('button', { name: 'Veto' }).click();
      await row.getByRole('button', { name: 'Confirm veto' }).click();
      for (const page of [facilitator, display, ...phones]) {
        await expect(page.getByText(/The Authority vetoed .+\. Vote again on the remaining lenses\./)).toBeVisible();
        await expect(page.getByTestId('lens-utilitarian').getByRole('button')).toHaveCount(0);
      }
      // one veto per game: two lenses remain, so only the spent veto keeps the button away
      await expect(facilitator.getByRole('button', { name: 'Veto' })).toHaveCount(0);
    } else {
      await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
    }
    for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
    for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
    if (season === 1) {
      // A phone loses its connection mid-season (locked, asleep, Wi-Fi gone) and the vote closes while it is away: it
      // says so, reconnects by itself and receives its private turn from the resync. Another reloads the page and
      // rejoins its role from the stored token.
      const [dropped, reloaded] = phones;
      link.down = true;
      await link.cut();
      await expect(dropped!.getByText('Connection lost. Reconnecting…')).toBeVisible();
      await facilitator.getByRole('button', { name: 'Close the vote' }).click();
      link.down = false;
      await expect(dropped!.getByText('Connection lost. Reconnecting…')).toHaveCount(0, { timeout: 15_000 });
      await reloaded!.reload();
    } else {
      await facilitator.getByRole('button', { name: 'Close the vote' }).click();
    }

    // S6 on every phone; the first scheme borrows one unit, and the projector never shows a private turn
    for (const [i, phone] of phones.entries()) {
      await expect(phone.getByRole('heading', { name: 'Your turn' })).toBeVisible();
      if (i === 0) await phone.getByRole('button', { name: 'One more' }).click();
      await phone.getByRole('button', { name: 'Commit my turn' }).click();
    }
    await expect(display.getByText(/Private turns/)).toBeVisible();
    for (const phone of phones) await expect(phone.getByText(/Committed|what happened|The game lasted/).first()).toBeVisible();

    const next = facilitator.getByRole('button', { name: 'Open the next season' });
    const ended = facilitator.getByText(/The game lasted/);
    await expect(next.or(ended)).toBeVisible();
    if (await ended.isVisible()) break;

    // S7: the table sees the totals, each scheme its own result, the projector no scheme's
    await expect(display.getByRole('heading', { name: `Season ${season}: what happened` })).toBeVisible();
    await expect(display.getByText(/The table pumped/)).toBeVisible();
    await expect(display.getByLabel(/Your scheme/)).toHaveCount(0);
    for (const phone of phones) await expect(phone.getByLabel(/Your scheme/)).toBeVisible();
    open = next;
    expect(season).toBeLessThan(20);
  }

  // S8: each scheme sees its own goal; the projector none; the facilitator the brief, then opens the debrief
  for (const phone of phones) await expect(phone.getByText(/Your goal/)).toBeVisible();
  await expect(display.getByText(/The game lasted/)).toBeVisible();
  await expect(display.getByText(/Your goal/)).toHaveCount(0);
  await expect(display.getByText('Debrief brief')).toHaveCount(0);
  await expect(facilitator.getByText(/we debrief the rules, not the person/)).toBeVisible();
  await facilitator.getByRole('button', { name: /reveal who pumped/ }).click();

  // S9 on every device after a per-player debrief: the scheme sheet, the welfare slider, the verdict
  for (const page of [display, facilitator, ...phones]) {
    await expect(page.getByRole('heading', { name: 'Debrief' })).toBeVisible();
    await expect(page.getByRole('table', { name: /Each scheme/ })).toBeVisible();
    await expect(page.getByRole('slider')).toBeVisible();
  }
  await expect(display.getByTestId('verdict')).toContainText('The table chose');

  // S10: a scheme saves an answer; nobody else receives it
  const reviewer = phones[0]!;
  await reviewer.getByRole('tab', { name: 'Review form' }).click();
  await reviewer.getByRole('textbox').first().fill('We argued about the tail-end scheme.');
  await reviewer.getByRole('button', { name: 'Save' }).first().click();
  await expect(reviewer.getByRole('button', { name: 'Saved' })).toHaveCount(1);
  await phones[1]!.getByRole('tab', { name: 'Review form' }).click();
  await expect(phones[1]!.getByRole('button', { name: 'Saved' })).toHaveCount(0);
});

test('a commit made while the connection drops is kept and sent again after reconnecting', async ({ browser }) => {
  const facilitator = await newPage(browser);
  await facilitator.goto('/');
  await facilitator.getByRole('button', { name: 'Open a room' }).click();
  const heading = await facilitator.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  const code = (heading ?? '').replace('Room ', '').trim();
  const display = await newPage(browser);
  await display.goto((await facilitator.getByRole('link', { name: 'Open the projector view' }).getAttribute('href')) ?? '');

  // The first phone's socket can be cut, and its next commit can be lost together with the connection.
  const link = { down: false, loseCommit: false, cut: () => Promise.resolve() };
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    if (i === 0) {
      await phone.routeWebSocket(/\/rooms\/[^/]+\/ws$/, async ws => {
        if (link.down) { await ws.close({ code: 1001, reason: 'no network' }); return; }
        const server = ws.connectToServer();
        link.cut = async () => { await ws.close({ code: 1001, reason: 'no network' }); await server.close(); };
        ws.onMessage(message => {
          if (link.loseCommit && String(message).includes('"intent":"commit"')) { link.loseCommit = false; void link.cut(); return; }
          server.send(message);
        });
      });
    }
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /will take part/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  const [cutPhone, ...others] = phones;

  // Practice round: the commit leaves the phone, but the connection dies before it reaches the server.
  await facilitator.getByRole('button', { name: 'Start the practice round' }).click();
  await facilitator.getByTestId('lens-utilitarian').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await facilitator.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of others) await phone.getByRole('button', { name: 'Commit my turn' }).click();
  link.loseCommit = true;
  await cutPhone!.getByRole('button', { name: 'Commit my turn' }).click();
  await expect(display.getByRole('heading', { name: /Practice round: what happened/ })).toBeVisible();

  // Season 1: the connection is already gone when the undo window ends, so the commit cannot be sent at all.
  await facilitator.getByRole('button', { name: 'Open season 1', exact: true }).click();
  await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await facilitator.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of others) await phone.getByRole('button', { name: 'Commit my turn' }).click();
  await expect(cutPhone!.getByRole('heading', { name: 'Your turn' })).toBeVisible();
  await cutPhone!.getByRole('button', { name: 'Commit my turn' }).click();
  link.down = true;
  await link.cut();
  await expect(cutPhone!.getByText('Not connected. Your turn is kept and will be sent when the connection is back.')).toBeVisible();
  await expect(cutPhone!.getByRole('heading', { name: 'Your turn' })).toBeVisible();
  await expect(display.getByText(/Private turns/)).toBeVisible(); // the season waits for the missing commit
  link.down = false;
  await expect(display.getByRole('heading', { name: 'Season 1: what happened' })).toBeVisible();
  await expect(cutPhone!.getByLabel(/Your scheme/)).toBeVisible();
});

test('a phone gone during its private turn: the server commits for it and the season resolves (ADR 0013)', async ({ browser }) => {
  const facilitator = await newPage(browser);
  await facilitator.goto('/');
  await facilitator.getByRole('button', { name: 'Open a room' }).click();
  const heading = await facilitator.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  const code = (heading ?? '').replace('Room ', '').trim();
  const display = await newPage(browser);
  await display.goto((await facilitator.getByRole('link', { name: 'Open the projector view' }).getAttribute('href')) ?? '');

  const link = { down: false, cut: () => Promise.resolve() };
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    if (i === 0) {
      await phone.routeWebSocket(/\/rooms\/[^/]+\/ws$/, async ws => {
        if (link.down) { await ws.close({ code: 1001, reason: 'no network' }); return; }
        const server = ws.connectToServer();
        link.cut = async () => { await ws.close({ code: 1001, reason: 'no network' }); await server.close(); };
      });
    }
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /will take part/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  const [gone, ...others] = phones;
  await facilitator.getByRole('button', { name: 'Skip it and open season 1' }).click();
  await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await facilitator.getByRole('button', { name: 'Close the vote' }).click();
  await expect(gone!.getByRole('heading', { name: 'Your turn' })).toBeVisible();
  link.down = true; // the phone is gone for good: dead battery, left in a bag
  await link.cut();
  await gone!.close();
  for (const phone of others) await phone.getByRole('button', { name: 'Commit my turn' }).click();
  await expect(display.getByText(/Private turns/)).toBeVisible();
  // the server's deadline: decisionS (45 s) plus the 10 s grace from the private turn's opening
  await expect(display.getByRole('heading', { name: 'Season 1: what happened' })).toBeVisible({ timeout: 90_000 });
  for (const page of [display, facilitator, ...others]) await expect(page.getByText(/time(d)? ?out/i)).toHaveCount(0);
});
