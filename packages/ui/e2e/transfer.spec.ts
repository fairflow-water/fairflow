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
