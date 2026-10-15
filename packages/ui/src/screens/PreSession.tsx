// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S2, the part before the session (blueprint R3, §5.0 "before"; ADR 0016, proposed), on the player's own phone from the
// link sent the day before: the personal linking code, kept on this phone for the join. No room exists yet, so nothing
// is sent anywhere. The pre-session survey comes here once the domain lead's instruments exist (content/surveys/).
// Consent stays at the join for now (ADR 0011).
import { useState } from 'react';
import recipe from '../../../../content/linking-code.json';
import { linkingStore, normaliseCode } from '../linking';

export function PreSession() {
  const [draft, setDraft] = useState('');
  const [kept, setKept] = useState<string | null>(() => linkingStore.get());
  const code = normaliseCode(draft);
  return (
    <section aria-labelledby="pre-title" className="join">
      <h1 id="pre-title">Before the session</h1>
      <h2>{recipe.title}</h2>
      <p>{recipe.intro}</p>
      <p>{recipe.recipe}</p>
      <p className="hint">{recipe.example}</p>
      <p className="hint"><em>{recipe.placeholderNote}</em></p>
      <label htmlFor="linking-code">{recipe.title}</label>
      <input id="linking-code" type="text" autoComplete="off" autoCapitalize="characters" value={draft}
        onChange={e => setDraft(e.target.value)} />
      <button type="button" disabled={code === ''} onClick={() => { linkingStore.set(code); setKept(code); }}>
        Keep this code on this phone
      </button>
      {kept && <p role="status">Kept on this phone: {kept}. Bring this phone to the session.</p>}
      <h2>Pre-session survey</h2>
      <p className="hint">{recipe.presurveyPending}</p>
    </section>
  );
}
