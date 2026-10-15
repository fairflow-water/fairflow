// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
// R3, S2 (ADR 0016, proposed): the personal linking code is made before the session on the player's own phone, kept
// on that phone, and sent with the join. The shared join screen asks for nothing typed.
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import recipe from '../../../content/linking-code.json';
import { linkingStore, normaliseCode } from './linking';
import { Join } from './screens/Join';
import { PreSession } from './screens/PreSession';
import opening from './fixtures/opening-public.json';
import type { PublicScenario } from './room';

const scenario = opening.scenario as PublicScenario;
const CODE = 'AB03'; // test input: the recipe's own example code

beforeEach(() => { localStorage.clear(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('linking code (R3)', () => {
  it('is normalised the way the engine accepts it: capitals and digits, within the shared bound', () => {
    expect(normaliseCode(' ab-03 ')).toBe(CODE);
    expect(normaliseCode('a'.repeat(recipe.maxLength + 5))).toHaveLength(recipe.maxLength);
    expect(normaliseCode('—')).toBe('');
  });
  it('the pre-session page keeps the code on this phone and says the survey is not ready', async () => {
    render(<PreSession />);
    expect(screen.getByText(recipe.placeholderNote)).toBeTruthy(); // the recipe waits for the domain lead
    expect(screen.getByText(recipe.recipe)).toBeTruthy();
    expect(screen.getByText(recipe.presurveyPending)).toBeTruthy();
    await userEvent.type(screen.getByRole('textbox', { name: recipe.title }), 'ab 03');
    await userEvent.click(screen.getByRole('button', { name: 'Keep this code on this phone' }));
    expect(linkingStore.get()).toBe(CODE);
    expect(screen.getByText(new RegExp(`Kept on this phone: ${CODE}`))).toBeTruthy();
  });
  it('an empty code is not kept', async () => {
    render(<PreSession />);
    expect((screen.getByRole('button', { name: 'Keep this code on this phone' }) as HTMLButtonElement).disabled).toBe(true);
    expect(linkingStore.get()).toBeNull();
  });
  it('the join sends the code kept on this phone, shows it, and asks for nothing typed', async () => {
    linkingStore.set(CODE);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ room: 'ABCDE', freeRoles: ['A'], phase: 'lobby', scenario, researchEnabled: false })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ token: 't', role: 'A' })));
    vi.stubGlobal('fetch', fetchMock);
    const onJoined = vi.fn();
    render(<Join code="ABCDE" onJoined={onJoined} />);
    await screen.findByText(scenario.name);
    expect(screen.getByText(new RegExp(CODE))).toBeTruthy();
    expect(screen.queryByRole('textbox')).toBeNull();
    await userEvent.click(screen.getByRole('checkbox', { name: /will take part/ }));
    await userEvent.click(screen.getAllByRole('button')[0]!);
    await vi.waitFor(() => expect(onJoined).toHaveBeenCalledWith('t'));
    const body = JSON.parse(String((fetchMock.mock.calls[1] as [string, RequestInit])[1].body)) as Record<string, unknown>;
    expect(body['linkingCode']).toBe(CODE);
  });
  it('without a kept code the join sends none', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ room: 'ABCDE', freeRoles: ['A'], phase: 'lobby', scenario, researchEnabled: false })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ token: 't', role: 'A' })));
    vi.stubGlobal('fetch', fetchMock);
    const onJoined = vi.fn();
    render(<Join code="ABCDE" onJoined={onJoined} />);
    await screen.findByText(scenario.name);
    await userEvent.click(screen.getByRole('checkbox', { name: /will take part/ }));
    await userEvent.click(screen.getAllByRole('button')[0]!);
    await vi.waitFor(() => expect(onJoined).toHaveBeenCalledWith('t'));
    const body = JSON.parse(String((fetchMock.mock.calls[1] as [string, RequestInit])[1].body)) as Record<string, unknown>;
    expect('linkingCode' in body).toBe(false);
  });
  it('while research is enabled, a phone with no code is sent to make one before any scheme is shown', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ room: 'ABCDE', freeRoles: ['A'], phase: 'lobby', scenario, researchEnabled: true }))));
    render(<Join code="ABCDE" onJoined={() => undefined} />);
    await screen.findByText(scenario.name);
    await userEvent.click(screen.getByRole('checkbox', { name: /will take part/ }));
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    expect(screen.queryByText('Choose your irrigation scheme')).toBeNull();
    expect(screen.getByRole('link', { name: 'Make your personal linking code first' }).getAttribute('href')).toBe('/pre');
  });
  it('a duplicate code refuses the join: "Choose a different code.", a link to /pre, and the kept code cleared', async () => {
    linkingStore.set(CODE);
    const refused = { detail: { code: 'duplicate_linking_code', message: '' } };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ room: 'ABCDE', freeRoles: ['A'], phase: 'lobby', scenario, researchEnabled: false })))
      .mockResolvedValueOnce(new Response(JSON.stringify(refused), { status: 409 }));
    vi.stubGlobal('fetch', fetchMock);
    const onJoined = vi.fn();
    render(<Join code="ABCDE" onJoined={onJoined} />);
    await screen.findByText(scenario.name);
    await userEvent.click(screen.getByRole('checkbox', { name: /will take part/ }));
    await userEvent.click(screen.getAllByRole('button')[0]!);
    // the maintainer, 2026-10-15: only this text; nothing about anyone else
    expect((await screen.findByRole('status')).textContent).toBe('Choose a different code.');
    expect(screen.getByRole('link', { name: 'Make a different code' }).getAttribute('href')).toBe('/pre');
    expect(linkingStore.get()).toBeNull(); // the kept code is cleared
    expect(localStorage.length).toBe(0); // and no role token was kept: the join was refused
    expect(onJoined).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Continue' })).toBeNull();
  });
});
