// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// A whole game in real browsers (ADR 0005): a facilitator opens a room, a projector and three phones join (each in its
// own browser context, so each holds only its own token); the table plays to the end, opens the debrief and one farm
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

  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /agree to take part/ }).check();
    await phone.getByRole('checkbox', { name: /pre-session questions/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  await expect(facilitator.getByRole('button', { name: 'Open season 1' })).toBeVisible();

  let open = facilitator.getByRole('button', { name: 'Open season 1' });
  for (let season = 1; ; season++) {
    await open.click();
    await facilitator.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
    for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
    for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
    await facilitator.getByRole('button', { name: 'Close the vote' }).click();

    // S6 on every phone; the first farm borrows one unit, and the projector never shows a private turn
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

    // S7: the table sees the totals, each farm its own result, the projector no farm's
    await expect(display.getByRole('heading', { name: `Season ${season}: what happened` })).toBeVisible();
    await expect(display.getByText(/The table pumped/)).toBeVisible();
    await expect(display.getByLabel(/Your farm/)).toHaveCount(0);
    for (const phone of phones) await expect(phone.getByLabel(/Your farm/)).toBeVisible();
    open = next;
    expect(season).toBeLessThan(20);
  }

  // S8: each farm sees its own goal; the projector none; the facilitator the brief, then opens the debrief
  for (const phone of phones) await expect(phone.getByText(/Your goal/)).toBeVisible();
  await expect(display.getByText(/The game lasted/)).toBeVisible();
  await expect(display.getByText(/Your goal/)).toHaveCount(0);
  await expect(display.getByText('Debrief brief')).toHaveCount(0);
  await expect(facilitator.getByText(/we debrief the rules, not the person/)).toBeVisible();
  await facilitator.getByRole('button', { name: /reveal who pumped/ }).click();

  // S9 on every device after a per-player debrief: the farm sheet, the welfare slider, the verdict
  for (const page of [display, facilitator, ...phones]) {
    await expect(page.getByRole('heading', { name: 'Debrief' })).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByRole('slider')).toBeVisible();
  }
  await expect(display.getByTestId('verdict')).toContainText('You voted for');

  // S10: a farm saves an answer; nobody else receives it
  const reviewer = phones[0]!;
  await reviewer.getByRole('tab', { name: 'Review form' }).click();
  await reviewer.getByRole('textbox').first().fill('We argued about the tail-end farm.');
  await reviewer.getByRole('button', { name: 'Save' }).first().click();
  await expect(reviewer.getByRole('button', { name: 'Saved' })).toHaveCount(1);
  await phones[1]!.getByRole('tab', { name: 'Review form' }).click();
  await expect(phones[1]!.getByRole('button', { name: 'Saved' })).toHaveCount(0);
});
