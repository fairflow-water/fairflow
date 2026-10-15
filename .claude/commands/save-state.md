---
description: Write the project's current state to docs/context/state.md and append a dated entry to docs/context/state-history.md
---

Save the current state of Fairflow so that the next session starts from it (CLAUDE.md imports `docs/context/state.md`).

1. **Gather facts from their sources, not from memory alone.**
   - `git fetch` then `git log --oneline -1 origin/main` for main's commit, and `gh run list --branch main --limit 3` for whether main is green.
   - `gh pr list --state open` and `gh issue list --state open` for what is open, and `gh pr list --state merged --limit 15` for what was merged recently.
   - `docs/handoff.md` §6 (decision records), §8 (next work) and §9 (waiting on the maintainer).
   - The maintainer's decisions given in this session, quoted or closely paraphrased, each with its date.
   - Every number, commit or PR reference comes from these commands or files. Do not work anything out by hand.

2. **Overwrite `docs/context/state.md`** with these sections, keeping its SPDX header:
   - **As of**: today's date and main's short commit.
   - **Merged**: recent PRs, one line each: number, title, and the decision behind it.
   - **Open**: PRs (with draft status and what each waits for) and issues.
   - **Decisions**: the maintainer's standing decisions and rules that are not yet in an accepted ADR or in the handoff, each with its date.
   - **Open questions**: what waits on the maintainer, with the PR, ADR or issue where it is written.
   - **Next steps**: in order, marking which need a decision first.

   Keep it short: a page, not a log. Name the irrigation schemes as schemes, never as farms.

3. **Append to `docs/context/state-history.md`** a section headed `## <date> <main's short commit>` with a one-paragraph summary of what changed since the previous entry. Never edit earlier entries.

4. **Do not commit or push unless the maintainer asks.** If asked, commit on a branch with `git commit -s` and open a PR under the merge rule; never push to main.

5. Report in two or three lines what changed in the state.
