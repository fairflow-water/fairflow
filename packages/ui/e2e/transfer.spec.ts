// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// ADR 0018, issue #9, in real browsers: the Authority moves an irrigation scheme to a new phone with a one-time link,
// and then passes the Authority role itself to another device. Each new device plays on; each old one is told the role
// has moved. Each device is its own browser context, so each holds only its own token.
import { expect, test, type Browser, type Page } from '@playwright/test';

const PHONE = { viewport: { width: 360, height: 640 } }; // §5.1: 360 × 640 portrait first

async function newPage(browser: Browser, options = {}): Promise<Page> {
  const context = await browser.newContext(options);
  return context.newPage();
}

async function linkFor(host: Page, button: string, role: string): Promise<string> {
  const panel = host.locator('details.move-role');
  if (!(await panel.evaluate(e => (e as HTMLDetailsElement).open))) await panel.locator('summary').click();
  await host.getByRole('button', { name: button }).click();
  const shown = host.locator(`.transfer-link[data-role="${role}"] p`).filter({ hasText: '/transfer/' });
  await expect(shown).toBeVisible();
  return (await shown.textContent()) ?? '';
}

test('a scheme moves to a new phone, then the Authority hands over, and both play on', async ({ browser }) => {
  const host = await newPage(browser);
  await host.goto('/');
  await host.getByRole('button', { name: 'Open a room' }).click();
  const heading = await host.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  const code = (heading ?? '').replace('Room ', '').trim();

  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /will take part/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  const first = phones[0]!;
  const schemeName = (await host.getByRole('list', { name: 'Irrigation schemes at the table' }).getByRole('listitem').first().textContent() ?? '').split(':')[0]!;

  // An irrigation scheme moves: the new phone opens the one-time link and waits in the lobby; the old phone is told
  const schemeLink = await linkFor(host, `Move ${schemeName}`, 'A');
  expect(schemeLink).toContain(`/transfer/${code}#`);
  const newPhone = await newPage(browser, PHONE);
  await newPhone.goto(schemeLink);
  await expect(newPhone.getByText(/Waiting for the facilitator/)).toBeVisible();
  await expect(newPhone).toHaveURL(new RegExp(`/join/${code}$`)); // the link has left the address
  await expect(first.getByText('This role now plays on another phone. You can close this page.')).toBeVisible();

  // The Authority hands over: the new device holds the room and can start the practice round
  const authorityLink = await linkFor(host, 'Pass the Authority role', 'authority');
  const newHost = await newPage(browser);
  await newHost.goto(authorityLink);
  await newHost.getByRole('button', { name: `Continue room ${code}` }).click();
  await expect(host.getByText('This role now plays on another phone. You can close this page.')).toBeVisible();
  await newHost.getByRole('button', { name: 'Start the practice round' }).click();
  for (const phone of [newPhone, ...phones.slice(1)]) {
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeHidden();
  }
});

test('at the hand-over season the Authority is asked to pass the role on, and the next student plays on (ADR 0018)', async ({ browser }) => {
  const host = await newPage(browser, PHONE); // the Authority is a student with a phone (ADR 0018, several tables)
  await host.goto('/');
  const choice = host.getByRole('combobox', { name: /Pass the Authority role to another student/ });
  await choice.selectOption({ label: 'After season 1' });
  await host.getByRole('button', { name: 'Open a room' }).click();
  const heading = await host.getByRole('heading', { level: 1, name: /^Room / }).textContent();
  const code = (heading ?? '').replace('Room ', '').trim();
  const phones: Page[] = [];
  for (let i = 0; i < 3; i++) {
    const phone = await newPage(browser, PHONE);
    await phone.goto(`/join/${code}`);
    await phone.getByRole('checkbox', { name: /will take part/ }).check();
    await phone.getByRole('list').getByRole('button').first().click();
    await expect(phone.getByText(/Waiting for the facilitator/)).toBeVisible();
    phones.push(phone);
  }
  await host.getByRole('button', { name: 'Skip it and open season 1' }).click();
  await host.getByTestId('lens-proportional').getByRole('button', { name: 'Propose' }).click();
  for (const phone of phones) await phone.getByTestId('lens-proportional').getByRole('button', { name: 'Vote' }).click();
  for (const phone of phones) await expect(phone.getByTestId('lens-proportional').getByRole('button', { name: 'Your vote' })).toBeVisible();
  await host.getByRole('button', { name: 'Close the vote' }).click();
  for (const phone of phones) await phone.getByRole('button', { name: 'Commit my turn' }).click();

  // the reveal of season 1: only the Authority's device asks, and the QR link moves the role
  await expect(host.getByRole('heading', { name: 'Season 1: what happened' })).toBeVisible();
  await expect(host.getByRole('heading', { name: 'Pass the Authority role' })).toBeVisible();
  for (const phone of phones) await expect(phone.getByRole('heading', { name: 'Pass the Authority role' })).toHaveCount(0);
  await host.getByRole('button', { name: 'Show the code for the next Authority' }).click();
  const shown = host.locator('.handover .transfer-link p').filter({ hasText: '/transfer/' });
  await expect(shown).toBeVisible();
  await expect(host.getByRole('img', { name: /QR code to become the Authority/ })).toBeVisible();
  const next = await newPage(browser, PHONE);
  await next.goto((await shown.textContent()) ?? '');
  await next.getByRole('button', { name: `Continue room ${code}` }).click();
  await expect(host.getByText('This role now plays on another phone. You can close this page.')).toBeVisible();

  // the new Authority is not asked again, and opens season 2 for the table
  await expect(next.getByRole('heading', { name: 'Season 1: what happened' })).toBeVisible();
  await expect(next.getByRole('heading', { name: 'Pass the Authority role' })).toHaveCount(0);
  await next.getByRole('button', { name: 'Open the next season' }).click();
  for (const phone of phones) await expect(phone.getByText('Season 2', { exact: true })).toBeVisible();
});
