// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// S10 — the review form (blueprint §5.2 S10, §5.4), parts 1–3 from content/review-form.json. Drafts are kept on this
// device so the form can be resumed; "Save" records the answer as a review.answer event, which only its author ever
// receives. Storage failures (private windows, blocked storage) are tolerated: the form still works, drafts are not kept.
import { useState } from 'react';
import form from '../../../../content/review-form.json';

const read = (key: string): Record<string, string> => {
  try { return JSON.parse(localStorage.getItem(key) ?? '{}') as Record<string, string>; } catch { return {}; }
};
const write = (key: string, value: Record<string, string>) => {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* drafts are a convenience */ }
};

export function Review({ storageKey, saved, onIntent }: {
  storageKey: string; saved: Record<string, string>; onIntent: (intent: Record<string, unknown>) => void;
}) {
  const [part, setPart] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, string>>(() => ({ ...saved, ...read(storageKey) }));
  const current = form.parts[part];
  if (!current) return null;
  const done = form.parts.flatMap(p => p.items).filter(i => saved[i.id]).length;
  const total = form.parts.flatMap(p => p.items).length;

  function edit(id: string, value: string) {
    const next = { ...drafts, [id]: value };
    setDrafts(next);
    write(storageKey, next);
  }

  return (
    <section aria-labelledby="review-title" className="review">
      <h2 id="review-title">Review</h2>
      <p className="hint">{done} of {total} answers saved. Your answers are sent to the room server; other players and the facilitator do not see them. The server keeps them only while it runs, so export the record to keep a copy.</p>
      <div role="tablist" aria-label="Parts" className="tabs">
        {form.parts.map((p, i) => (
          <button key={p.part} type="button" role="tab" aria-selected={i === part} onClick={() => setPart(i)}>Part {p.part}</button>
        ))}
      </div>
      <h3>{current.title}</h3>
      <p>{current.intro}</p>
      {current.items.map(item => {
        const value = drafts[item.id] ?? '';
        const isSaved = saved[item.id] === value && value !== '';
        return (
          <div key={item.id} className="answer">
            <label htmlFor={`review-${item.id}`}>{item.prompt}</label>
            <textarea id={`review-${item.id}`} value={value} maxLength={4000} rows={3} onChange={e => edit(item.id, e.target.value)} />
            <button type="button" disabled={value.trim() === '' || isSaved}
              onClick={() => onIntent({ intent: 'review_answer', part: current.part, item: item.id, value })}>
              {isSaved ? 'Saved' : 'Save'}
            </button>
          </div>
        );
      })}
    </section>
  );
}
