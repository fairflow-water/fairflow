<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0004 — What the table sees during play, so that individual pumping stays private

- Status: **accepted** in part, 2026-10-05: the maintainer chose option (ii) below with a 1 Mm³ tank (recommended after the research and measurements here). Items 5–6 (audit threshold, claim wording) and the S7 triangle were accepted by the maintainer on 2026-10-06. Amends R17–R19, S3, S6, S7, S9 and §6.2, §2.2, §2.6.

## Context

- **The problem.** R17–R18 promise that who pumped how much stays private until the debrief. But every public §6.2 field is computed on actual water use W = Q + P, the allocation Q is public, and the schemes differ in β, area and people. So the public numbers let anyone solve for each scheme's pumping.
  - With least squares on the Python engine, every scheme's pumping was recovered in 60 of 60 test seasons from the §6.2 public fields.
  - From the S7 reveal set alone (ΣP, S, E_PJ, E_SE, F), it was recovered in 45 of 45, and in 42 of 45 even when rounded to 2 decimals.
- **Literature** (sources in the session report; key ones below):
  - Commons experiments keep decisions private and announce only the group total or the resource state (Ostrom 2009; Cárdenas & Ostrom 2004; Meinzen-Dick et al. 2016).
  - Players are explicitly allowed to compute "group total − mine". Revealing individual extraction tends to raise extraction (Dubois et al. 2020; Bigoni & Suetens 2012).
  - Statistical disclosure control (Hundepool et al. 2025): with 3 contributors only exact disclosure can be prevented, and rounding or banding can be "unpicked" by combining outputs.
  - Differential privacy is unsuitable here: with n = 3 the noise is the size of the signal.

## Measured leakage (`packages/engine-py/analysis/privacy_leakage.py`; results in `analysis/privacy_leakage_results.md` and `privacy_leakage_rationing.md`)

- **Method:**
  - The default basin with the shipped β; candidate pumping vectors on a 0.1 Mm³ grid.
  - 400 seasons at normal stock (B_low to B₀).
  - 200 seasons at low stock through the real engine path, with rationing (111 of the 200 seasons were rationed).
- **Definitions:**
  - "Identified" means every candidate consistent with the display agrees within 0.1 Mm³.
  - An insider is another player who knows their own pumping.
  - Brackets are 95 % Wilson intervals.
- An earlier 30–45-season run was too small: its estimates moved by up to 27 points with the random seed. It is superseded by these results.

| In-play display (normal stock) | Outsider: identified | Outsider: knows whether pumped | Insider: identified | Insider: knows whether pumped |
|---|---|---|---|---|
| A. §6.2 as written | 100 % | 100 % | 100 % | 100 % |
| B. ΣP + exact tank, dials on allocation only | 37 % (34–40) | 65 % (62–68) | 100 % | 100 % |
| E. ΣP only — the floor while ΣP is public | 9 % (7–10) | 10 % (9–12) | 38 % (35–40) | 57 % (54–59) |
| G. ΣP + tank to 1 Mm³ + all actual-use band words | 17 % (15–19) | 38 % (36–41) | 50 % (47–52) | 82 % (80–84) |
| **I. ΣP + tank to 1 Mm³ + sustainability band only (implemented)** | **10 % (9–12)** | **18 % (16–21)** | **41 % (39–44)** | **68 % (65–70)** |

| Low stock, real engine path with rationing | Outsider: identified | Outsider: knows whether pumped | Insider: identified | Insider: knows whether pumped |
|---|---|---|---|---|
| Floor: rationed ΣP only | 8 % (7–11) | 6 % (4–8) | 22 % (18–25) | 30 % (26–33) |
| **Implemented: public part of season.resolved** | **9 % (7–12)** | **12 % (10–15)** | **23 % (20–26)** | **40 % (36–44)** |

**What the numbers show:**
- On identical seasons the implemented public output and the simulated design I give identical feasible sets.
- Exact identification is indistinguishable from the floor at both stock levels.
- What remains is knowledge of *whether* a scheme pumped: +6 to +11 points above the floor, mostly from the tank level.
- The floor itself is inherent: with three schemes, the public total tells each player what the other two did together. This is standard in commons games and acceptable under SDC norms.

## Decision (proposed)

1. **During play, the equity and efficiency dials are computed on the allocation Q** (public, so they disclose nothing). Their values on actual use (W) are shown at the debrief, exactly.
2. **Total pumping ΣP is public and exact** (R17, as in every commons game).
3. **Sustainability is shown during play as its band word only** (good / warning / unsustainable, with the registry's fixed band edges), keeping "the pumps move sustainability" (§1). Equity and efficiency get no actual-use band words during play: they cost the most privacy (row J).
4. **The aquifer tank is shown at a coarse resolution.** The resolution is an admin-settable display parameter; 1 Mm³ was measured. The exact stock moves from the public to the sealed part of `season.resolved`. The public part carries the coarse level.
5. **A feasibility audit is a release gate:** `analysis/privacy_leakage.py` is run on every shipped scenario, and the in-play display may not exceed thresholds the maintainer sets (accepted 2026-10-06: "identified" within the floor's 95 % interval, and "knows whether pumped" no more than 12 points above the floor).
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

## Maintainer decision (2026-10-05)

| Question | Decision |
|---|---|
| Exact-stock channels | option (ii): pump cost and GW–SW coupling are computed from the observed tank level |
| Tank resolution | 1 Mm³ (admin-settable per scenario) |
| Observed level | the last full step below the true stock, floor(B / resolution) × resolution, as a tank gauge shows completed segments |

The true stock, return flows by irrigation method and the mass balance are unchanged and exact in the record. Only what players perceive, and what prices their pumping, is coarse. Rationing at B_res uses the true stock: it is physical.

## Consequences

- Engine:
  - `season.resolved` public part: ΣP, allocation-based dials, sustainability band, coarse tank. Sealed part: exact stock, actual-use dials, per-scheme values.
  - New registry parameter: tank display resolution.
  - The projection tests extend to the feasibility audit.
- Moved to the debrief by this decision, because each is computed on actual use:
  - the per-season verdict, welfare scores, Gini and triangle;
  - the crop-failure flag.

  The collective score and crop-failure flag appear at game end (S8), after play. **Decided 2026-10-06:** S7 beat 3 shows no triangle during play; the triangle appears per season in the debrief replay (S9), on the exact values. During play the table sees the as-allocated dials, the sustainability band word and the tank. A coarse in-play triangle would either leak pumping or require inventing a binned formula.
- Screens:
  - S7 beat 2 shows the allocation-based equity needles, labelled "as allocated".
  - S7 beat 1 shows the sustainability band word and the coarse tank.
  - S9 shows both "as allocated" and "as used". That contrast is a new debrief moment: how pumping changed the fairness the table voted for.
  - **Totals-only debrief (implemented 2026-10-07; for the maintainer to confirm).** R19 lets a table keep per-player pumping sealed (`debrief.opened {perPlayer: false}`). By the measurements above, the exact as-used values (dials, triangle, welfare, verdict) let the table solve for each farm's pumping, so in that case they stay sealed as well. S9 then shows the as-allocated values, total pumping and the welfare slider over the lenses' allocations, and says why the rest is hidden. With `perPlayer: true` everything is opened.
- Research: hypotheses 3–4 (§10.3) are unaffected. Pumping stays a hidden action, as the design intended.
