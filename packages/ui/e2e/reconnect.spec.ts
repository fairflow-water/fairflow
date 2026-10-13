// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Reconnection in every phase (handoff §8 item 6, E7): one phone is reloaded, and separately put to sleep (its socket
// cut, as a locked phone or lost Wi-Fi does) while the table moves on, in each phase of a game. After each, the phone
// must show what it should for that phase. Each check is recorded as works / fails and the table is printed; the test
// fails if any phase fails that is not listed in KNOWN with its issue.
import { expect, test, type Browser, type Page } from '@playwright/test';

const PHONE = { viewport: { width: 360, height: 640 } };
const BACK_MS = 20_000; // layout: how long a phone may take to show the right screen after waking or reloading
// Phases that fail today, each with the issue that tracks it; a check listed here is reported, not failed.
const KNOWN: Record<string, string> = {};

interface Row { phase: string; check: string; result: 'works' | 'fails' | 'not reached'; detail: string }

async function newPage(browser: Browser, options = {}): Promise<Page> {
  return (await browser.newContext(options)).newPage();
}

test('a phone reloaded or asleep in every phase comes back to the right screen', async ({ browser }) => {
  test.setTimeout(600_000);
  const rows: Row[] = [];
  async function check(phase: string, kind: string, body: () => Promise<void>) {
    try {
      await body();
      rows.push({ phase, check: kind, result: 'works', detail: '' });
    } catch (e) {
      const detail = (e instanceof Error ? e.message : String(e)).split('\n').filter(l => l.trim()).slice(0, 3).join(' / ');
      rows.push({ phase, check: kind, result: 'fails', detail });
    }
  }

  const facilitator = await newPage(browser);
  await facilitator.goto('/');
  await facilitator.getByRole('button', { name: 'Open a room' }).click();
  const heading = await facilitator.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  const code = (heading ?? '').replace('Room ', '').trim();
  const display = await newPage(browser);
  await display.goto((await facilitator.getByRole('link', { name: 'Open the projector view' }).getAttribute('href')) ?? '');

  // phone 0 is the one tested; its socket runs through a route the test can cut
  const link = { down: false, cut: () => Promise.resolve() };
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    if (i === 0) {
      await phone.routeWebSocket(/\/rooms\/[^/]+\/ws$/, async ws => {
        if (link.down) { await ws.close({ code: 1001, reason: 'asleep' }); return; }
        const server = ws.connectToServer();
        link.cut = async () => { await ws.close({ code: 1001, reason: 'asleep' }); await server.close(); };
      });
    }
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /will take part/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  const [me, ...others] = phones as [Page, Page, Page];
  const reload = async (expectation: () => Promise<void>) => { await me.reload(); await expectation(); };
  /** Put the phone to sleep, let the table do `meanwhile`, wake it, and check what it shows. */
  const sleep = async (meanwhile: () => Promise<void>, expectation: () => Promise<void>) => {
    link.down = true;
    await link.cut();
    await expect(me.getByText('Connection lost. Reconnecting…')).toBeVisible();
    await meanwhile();
    link.down = false;
    await me.evaluate(() => window.dispatchEvent(new Event('online'))); // the phone wakes
    await expect(me.getByText('Connection lost. Reconnecting…')).toHaveCount(0, { timeout: BACK_MS });
    await expectation();
  };
  const nothing = () => Promise.resolve();
  const see = (locator: ReturnType<Page['getByText']>) => expect(locator.first()).toBeVisible({ timeout: BACK_MS });

  // ---- lobby
  await check('lobby', 'reload', () => reload(() => see(me.getByText(/Waiting for the facilitator to open season 1/))));
  await check('lobby', 'sleep', () => sleep(nothing, () => see(me.getByText(/Waiting for the facilitator/))));

  // ---- practice round: vote, private turn, reveal
  await facilitator.getByRole('button', { name: 'Start the practice round' }).click();
  await check('practice vote', 'reload', () => reload(() => see(me.getByTestId('lens-utilitarian'))));
  await check('practice vote', 'sleep', () => sleep(
    () => facilitator.getByTestId('lens-utilitarian').getByRole('button', { name: 'Propose' }).click(),
    () => see(me.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }))));
  for (const phone of phones) await phone.getByTestId('lens-utilitarian').getByRole('button', { name: 'Vote' }).click().catch(() => undefined);
  await facilitator.getByRole('button', { name: 'Close the vote' }).click();
  await see(others[0].getByRole('heading', { name: 'Your turn' }));
  await check('practice private turn', 'reload', () => reload(() => see(me.getByRole('heading', { name: 'Your turn' }))));
  await check('practice private turn', 'sleep', () => sleep(
    () => others[0].getByRole('button', { name: 'Commit my turn' }).click(),
    () => see(me.getByRole('heading', { name: 'Your turn' }))));
  await others[1].getByRole('button', { name: 'Commit my turn' }).click();
  await me.getByRole('button', { name: 'Commit my turn' }).click().catch(() => undefined);
  await see(display.getByRole('heading', { name: /Practice round: what happened/ }));
  await check('practice reveal', 'reload', () => reload(() => see(me.getByLabel(/Your scheme/))));
  await check('practice reveal', 'sleep', () => sleep(
    () => facilitator.getByRole('button', { name: 'Open season 1', exact: true }).click(),
    () => see(me.getByTestId('lens-proportional'))));
  if (await facilitator.getByRole('button', { name: 'Open season 1', exact: true }).isVisible()) {
    await facilitator.getByRole('button', { name: 'Open season 1', exact: true }).click();
  }

  // ---- seasons until the game ends: a tie in season 1, a floor vote when one is offered, then plain seasons
  let floorSeen = false;
  let tieSeen = false;
  for (let season = 1; season < 20; season++) {
    await see(facilitator.getByTestId('lens-proportional'));
    const floorOffered = !floorSeen
      && await facilitator.getByTestId('lens-sufficientarian').getByText(/Not enough for every minimum/).isVisible();
    if (season === 1) {
      // three lenses, one vote each: a tie the facilitator must break
      for (const lens of ['proportional', 'egalitarian', 'capability']) {
        await facilitator.getByTestId(`lens-${lens}`).getByRole('button', { name: 'Propose' }).click();
      }
      await check('lens vote', 'reload', () => reload(() => see(me.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }))));
      await check('lens vote', 'sleep', () => sleep(
        async () => {
          await others[0].getByTestId('lens-egalitarian').getByRole('button', { name: 'Vote' }).click();
          await others[1].getByTestId('lens-capability').getByRole('button', { name: 'Vote' }).click();
        },
        () => see(me.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }))));
      await me.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
      await facilitator.getByRole('button', { name: 'Close the vote' }).click();
      tieSeen = await facilitator.getByRole('button', { name: 'Break the tie' }).first()
        .waitFor({ timeout: BACK_MS }).then(() => true, () => false);
      if (tieSeen) {
        await check('tie-break', 'reload', () => reload(() => see(me.getByTestId('lens-proportional'))));
        await check('tie-break', 'sleep', () => sleep(
          () => facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Break the tie' }).click(),
          () => see(me.getByRole('heading', { name: /Your turn|Not enough for everyone's minimum/ }))));
        if (await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Break the tie' }).isVisible()) {
          await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Break the tie' }).click();
        }
      }
    } else if (floorOffered) {
      floorSeen = true;
      await facilitator.getByTestId('lens-sufficientarian').getByRole('button', { name: 'Propose' }).click();
      for (const phone of phones) await phone.getByTestId('lens-sufficientarian').getByRole('button', { name: 'Vote' }).click();
      await facilitator.getByRole('button', { name: 'Close the vote' }).click();
      await see(facilitator.getByRole('heading', { name: /Not enough for everyone's minimum/ }));
      await check('floor vote', 'reload', () => reload(() => see(me.getByRole('heading', { name: /Not enough for everyone's minimum/ }))));
      await check('floor vote', 'sleep', () => sleep(
        () => facilitator.getByRole('button', { name: 'Close the vote' }).click(),
        () => see(me.getByRole('heading', { name: 'Your turn' }))));
      if (await facilitator.getByRole('button', { name: 'Close the vote' }).isVisible()) {
        await facilitator.getByRole('button', { name: 'Close the vote' }).click();
      }
    } else {
      await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
      for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
      await facilitator.getByRole('button', { name: 'Close the vote' }).click();
    }

    await see(me.getByRole('heading', { name: 'Your turn' }));
    if (season === 2) {
      await check('private turn', 'reload', () => reload(() => see(me.getByRole('heading', { name: 'Your turn' }))));
      await check('private turn', 'sleep across its own commit', () => sleep(
        async () => {
          await me.getByRole('button', { name: 'Commit my turn' }).click(); // committed just as the phone locks
          await me.waitForTimeout(3500); // the 3 s undo ends while asleep
        },
        () => see(me.getByText(/Committed\. Waiting for the other schemes|Season \d+: what happened/))));
    }
    if (season === 1) {
      // issue #15: scheme B (the second seat taken, others[0]; the paddy cooperative, the largest demand) expands, so
      // from season 2 the sufficientarian floors exceed a dry year's water and a floor vote follows when that lens
      // wins; a game that draws no dry card after season 1 reports the phase not reached
      await others[0].getByRole('button', { name: /^Actions:/ }).click();
      await others[0].getByRole('radio', { name: /^Expand/ }).check();
    }
    for (const phone of [...others, me]) {
      const button = phone.getByRole('button', { name: 'Commit my turn' });
      if (await button.isVisible()) await button.click();
    }
    const next = facilitator.getByRole('button', { name: 'Open the next season' });
    const ended = facilitator.getByText(/The game lasted/);
    if (!await next.or(ended).first().waitFor({ timeout: BACK_MS }).then(() => true, () => false)) {
      // a turn stuck on this phone (a commit lost while asleep): reload it, as a player would, and commit again
      await me.reload();
      await me.getByRole('button', { name: 'Commit my turn' }).click();
    }
    await expect(next.or(ended)).toBeVisible({ timeout: BACK_MS });
    if (await ended.isVisible()) break;
    if (season === 2) {
      await check('reveal', 'reload', () => reload(() => see(me.getByLabel(/Your scheme/))));
      await check('reveal', 'sleep', () => sleep(() => next.click(), () => see(me.getByTestId('lens-proportional'))));
      if (await next.isVisible()) await next.click();
    } else {
      await next.click();
    }
  }
  if (!tieSeen) rows.push({ phase: 'tie-break', check: 'reload and sleep', result: 'not reached', detail: 'no tie arose' });
  if (!floorSeen) {
    rows.push({ phase: 'floor vote', check: 'reload and sleep', result: 'not reached', detail: 'no dry season after season 1 offered one (issue #15)' });
  }

  // ---- game end, debrief, review
  await check('game end', 'reload', () => reload(() => see(me.getByText(/Your goal/))));
  await check('game end', 'sleep', () => sleep(
    () => facilitator.getByRole('button', { name: /reveal who pumped/ }).click(),
    () => see(me.getByRole('heading', { name: 'Debrief' }))));
  if (await facilitator.getByRole('button', { name: /reveal who pumped/ }).isVisible()) {
    await facilitator.getByRole('button', { name: /reveal who pumped/ }).click();
  }
  await check('debrief', 'reload', () => reload(() => see(me.getByRole('table', { name: /Each scheme/ }))));
  await check('debrief', 'sleep', () => sleep(nothing, () => see(me.getByRole('table', { name: /Each scheme/ }))));
  await me.getByRole('tab', { name: 'Review form' }).click();
  await me.getByRole('textbox').first().fill('a draft typed before the reload');
  await check('review form', 'reload keeps a draft', () => reload(async () => {
    await me.getByRole('tab', { name: 'Review form' }).click();
    await expect(me.getByRole('textbox').first()).toHaveValue('a draft typed before the reload');
  }));
  await check('review form', 'sleep, then save', () => sleep(nothing, async () => {
    await me.getByRole('button', { name: 'Save' }).first().click();
    await expect(me.getByRole('button', { name: 'Saved' })).toHaveCount(1);
  }));

  console.log(['| Phase | Check | Result | Detail |', '|---|---|---|---|',
    ...rows.map(r => `| ${r.phase} | ${r.check} | ${r.result} | ${r.detail.replaceAll('|', '/')} |`)].join('\n'));
  await test.info().attach('reconnection.json', { body: JSON.stringify(rows, null, 1), contentType: 'application/json' });
  const unexpected = rows.filter(r => r.result === 'fails' && !KNOWN[`${r.phase}: ${r.check}`]);
  expect(unexpected).toEqual([]);
});
