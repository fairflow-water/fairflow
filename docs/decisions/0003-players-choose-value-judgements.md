<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0003 — Value judgements the blueprint leaves open go to the players

- Status: **accepted** by the maintainer, 2026-10-06. Amends blueprint §2.3, §2.7, R8, S4 and S9. Plain-language names and card backs for the floor options remain content work (§5.3).
- Context: two parameters of the model are moral choices that the blueprint leaves open:
  - **How the sufficientarian floors are cut when water is short of them.** §2.3 says "proportional scaling or CEA on floors if short" and names no default.
  - **The inequality aversion γ of the a posteriori prioritarian welfare score.** §2.7 gives PWF_γ; §3.1 tabulates it at γ = 3 ("PWF₃"); no default is stated.

  The game's premise is that "there is no lens-free way to share scarce water" (§1), and the debrief names the lens hidden in the scoreboard (§2.5). Fixing either value silently in configuration would contradict that premise. The maintainer asked that the choice not be a dichotomy, and that a table which does not want to choose ("whatever works") gets a proportional cut.

## Decision

### 1. The floor shortfall is decided by the table, from the claims rules already in the game

- **When it happens:** only when the sufficientarian lens wins a season in which the floors (floor × D_i) exceed the allocable water.
- **How it's decided:** a short follow-up vote on S4, with the same chips and the same Authority tie-break as R8.
- **The options are the §2.3 claims rules, applied with the floors as the claims.** No new equation is introduced; each option is an existing lens of §2.3 run on smaller claims.

| Option (plain name, ≤ 6 words) | Rule applied to the floors | Grounding |
|---|---|---|
| Same share of the minimum | proportional | Aristotle NE V.3; §2.3 |
| Protect the smallest minimums | constrained equal awards (CEA) | Aumann & Maschler 1985; Thomson 2003 |
| Everyone gives up the same | constrained equal losses (CEL) | Thomson 2003 |
| Half-claims first (Talmud) | Talmud rule | Aumann & Maschler 1985 |
| Per person | capability weights N_i·κ_i | Sen 1999; §2.3 |
| Whatever works | proportional | maintainer decision, 2026-10-05 |

- **The set is configurable per scenario:** an admin may offer fewer options. "Whatever works" is always offered, and it is also what applies on timer expiry with no proposal.
- **Recorded as a new event**, `lens.floorRule {rule, tally, byTimeout}` (public).

### 2. The γ of the welfare score is a debrief control, not a hidden constant

- S9 gains a labelled slider: "How much more should water to the worst-off farm count?"
  - Its low end ("every share counts the same") and high end ("only the worst-off counts") are the limiting cases of the Atkinson (1970) form.
  - It shows no number, so S9 stays within seven numbers.
  - Moving it recomputes only the PWF column.
- **Starting value:** the §3.1 reference value (γ = 3, "PWF₃"), labelled on screen as the reference value, not a verdict. A scenario may set another starting value.
- **Optional research measure (§10.2):** the pre-survey may elicit each player's own inequality aversion, so the slider starts at the table's median. This is a research-design decision for the pre-registration, not part of this ADR's default.

## Consequences

- Engine (Python authority first, then the TypeScript mirror): `floorScaling` accepts proportional | cea | cel | talmud | capability, applied to the floors as claims. Tests check:
  - the cut floors sum to AW;
  - no floor is exceeded;
  - each option equals the same lens run on a basin whose demands are the floors.
- Registry:
  - `lenses.sufficientarian.floorScaling` defaults to `proportional`, sourced to this ADR ("Whatever works | proportional").
  - `indicators.welfareGamma` starts at the §3.1 value (γ = 3), sourced to §3.1 and this ADR.
- Content: plain names and card backs for the options (≤ 60 words each, §5.1). Facilitator script: one debrief prompt on the floor vote when it occurred.
- Research: the floor-rule vote is a new in-game measure (who chose to protect whom), available in events.csv.
