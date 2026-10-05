<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0004 — What the table sees during play, so that individual pumping stays private

- Status: **proposed**, 2026-10-05. Direction chosen by the maintainer: allocation-based dials during play, plus coarse words for actual outcomes. Three model questions remain for the science reviewer (below). Amends R17–R19, S3, S6, S7 and §6.2.

## Context

- **The problem.** R17–R18 promise that who pumped how much stays private until the debrief. But every public §6.2 field is computed on actual water use W = Q + P, the allocation Q is public, and the schemes differ in β, area and people. So the public numbers let anyone solve for each scheme's pumping.
  - With least squares on the Python engine, every scheme's pumping was recovered in 60 of 60 test seasons from the §6.2 public fields.
  - From the S7 reveal set alone (ΣP, S, E_PJ, E_SE, F), it was recovered in 45 of 45, and in 42 of 45 even when rounded to 2 decimals.
- **Literature** (sources in the session report; key ones below):
  - Commons experiments keep decisions private and announce only the group total or the resource state (Ostrom 2009; Cárdenas & Ostrom 2004; Meinzen-Dick et al. 2016).
  - Players are explicitly allowed to compute "group total − mine". Revealing individual extraction tends to raise extraction (Dubois et al. 2020; Bigoni & Suetens 2012).
  - Statistical disclosure control (Hundepool et al. 2025): with 3 contributors only exact disclosure can be prevented, and rounding or banding can be "unpicked" by combining outputs.
  - Differential privacy is unsuitable here: with n = 3 the noise is the size of the signal.

## Measured leakage (`packages/engine-py/analysis/privacy_leakage.py`)

- **Method:** the default basin with the shipped β, 45 seasons over 3 cards and 5 lenses, and every pumping vector on a 0.1 Mm³ grid.
- **Definitions:**
  - "Identified" means all candidates consistent with the display agree within 0.1 Mm³.
  - An "insider" is another player who knows their own pumping.

| In-play display | Outsider: identified | Outsider: knows whether pumped | Insider: identified | Insider: knows whether pumped |
|---|---|---|---|---|
| A. §6.2 as written | 100 % | 100 % | 100 % | 100 % |
| B. ΣP + exact tank, dials on allocation only | 25 % | 60 % | 100 % | 100 % |
| C. ΣP + tank to 1 Mm³ | 4 % | 13 % | 35 % | 59 % |
| E. ΣP only (floor while ΣP is public) | 2 % | 7 % | 32 % | 51 % |
| G. ΣP + tank to 1 Mm³ + all actual-use band words | 10 % | 36 % | 45 % | 79 % |
| **I. ΣP + tank to 1 Mm³ + sustainability band only** | **4 %** | **17 %** | **35 %** | **60 %** |
| J. ΣP + tank to 1 Mm³ + equity bands only | 9 % | 30 % | 42 % | 74 % |

Row E is inherent: with three schemes, the public total tells each player what the other two did together. This is standard in commons games and acceptable under SDC norms. Anything above row E is extra disclosure.

## Decision (proposed)

1. **During play, the equity and efficiency dials are computed on the allocation Q** (public, so they disclose nothing). Their values on actual use (W) are shown at the debrief, exactly.
2. **Total pumping ΣP is public and exact** (R17, as in every commons game).
3. **Sustainability is shown during play as its band word only** (good / warning / unsustainable, with the registry's fixed band edges), keeping "the pumps move sustainability" (§1). Equity and efficiency get no actual-use band words during play: they cost the most privacy (row J).
4. **The aquifer tank is shown at a coarse resolution.** The resolution is an admin-settable display parameter; 1 Mm³ was measured. The exact stock moves from the public to the sealed part of `season.resolved`. The public part carries the coarse level.
5. **A feasibility audit is a release gate:** `analysis/privacy_leakage.py` is run on every shipped scenario, and the in-play display may not exceed thresholds the maintainer sets (proposal: no more than row I + 5 points).
6. **Claims are worded to match.** R17 changes to "individual pumping is not displayed and cannot be computed from what is displayed beyond what the total implies". The JOSS draft's "provably hidden" is replaced by this measured statement.

## Open — science reviewer (model equations, not display)

**Even with 1–5 in place, each player learns the exact stock privately, and then an insider recovers everyone's pumping (row B, insider 100 %).** There are three channels:

- **(a) Their own pump cost.** The cost per Mm³ depends on B (§2.2) and is shown on S6, and is also implied by their own ΔL.
- **(b) Next season's inflow** once B < B_low (GW–SW coupling, §2.6).
- **(c) The exact stock in any record they can open** (closed by item 4).

Three ways to close (a) and (b):

| Option | What changes | Effect | Cost |
|---|---|---|---|
| (i) Return flows from **pumped** water credited at the basin's demand-weighted β* instead of each scheme's β | an equation in §2.6 | Stock change no longer depends on who pumped, so closed by construction | The Perry/Grafton return-flow lesson is weaker for pumped water; the fixtures change |
| (ii) **Pump cost and coupling computed from the coarse tank level** | equations in §2.2 and §2.6 | No player learns B exactly | Costs and inflows move in steps |
| (iii) **Accept** | none | Insiders can identify others when n = 3 | Contradicts R18; the literature treats exact individual disclosure as unacceptable |

Also to decide:
- the tank resolution;
- the audit thresholds;
- whether 4–5-scheme tables (less leakage) may use a finer tank.

## Consequences

- Engine:
  - `season.resolved` public part: ΣP, allocation-based dials, sustainability band, coarse tank. Sealed part: exact stock, actual-use dials, per-scheme values.
  - New registry parameter: tank display resolution.
  - The projection tests extend to the feasibility audit.
- Screens:
  - S7 beat 2 shows the allocation-based equity needles, labelled "as allocated".
  - S7 beat 1 shows the sustainability band word and the coarse tank.
  - S9 shows both "as allocated" and "as used". That contrast is a new debrief moment: how pumping changed the fairness the table voted for.
- Research: hypotheses 3–4 (§10.3) are unaffected. Pumping stays a hidden action, as the design intended.
