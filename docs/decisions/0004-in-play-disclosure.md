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
  - Commons experiments keep each decision private and announce only the group total or the resource state (Cárdenas, Stranlund & Willis 2000; Cárdenas & Ostrom 2004; Meinzen-Dick et al. 2016). Players are taught to compute "group total − mine" (Cárdenas & Ostrom 2004, instructions in CAPRi Working Paper 32).
  - Whether revealing individual choices changes behaviour is mixed, and it is not the reason for privacy here. In repeated public-good games, information on others' individual contributions tends to raise cooperation and information on others' earnings lowers it (Sell & Wilson 1991; Bigoni & Suetens 2012; Fiala & Suetens 2017). In a common-pool resource experiment, mandatory disclosure of each member's extraction gave higher extraction than voluntary disclosure, with no aggregate-only arm (Dubois et al. 2020). Fairflow keeps pumping private because the hidden action is the dilemma it studies (R17–R18) and because this is the standard commons protocol.
  - Statistical disclosure control (Hundepool et al. 2025, *Handbook on Statistical Disclosure Control*, 2nd ed., §4.2.1 and §5.5): a minimum of 3 contributors guards only against exact disclosure, and conventional rounding can be unpicked by differencing and linking outputs.
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

## Amendment 2026-10-11/12: Kelvara re-measurement, an observed total, and a corrected gate (review B19)

- **Why.** The measurements above were made on the earlier default basin with independent-scheme intervals. The Kelvara basin (ADR 0007, 0008, 0009) changes what a table can infer: well capacities of 3.125 / 4.5 / 1.7 Mm³ make the exact total a fingerprint — the eight sums of farms pumping at capacity all have different fractional parts — and when the paddy smallholders' wells are dry only two farms can pump. The three schemes of a season also share one public record, so intervals must be computed over seasons, not over scheme-seasons.
- **Decision (implemented).**
  1. The table sees total pumping to the tank's resolution: `pumpsTotalObserved`, rounded half up to 1 Mm³; the exact total moves to the sealed part of `season.resolved`. The game-end brief and the Authority's published mean use the observed totals; the Authority's goal is still judged on the exact ones.
  2. `analysis/privacy_leakage.py` now loads the shipped scenario, uses the pump levels the private turn offers, includes each insider's own results, covers both stock regimes, and reports per-farm Wilson intervals over seasons, pooled cluster-bootstrap intervals, season-level "any farm identified" and the paired difference against the floor (`analysis/privacy_leakage_kelvara.md`).
  3. The gate is restated so that it does not tighten as more seasons are run: at 1,000 seasons per regime, over farms that can pump, the upper 95 % bound of (implemented − floor) is at most 5 points for "identified" (margin to be confirmed by the maintainer) and at most 12 points for "knows whether pumped".
- **What the re-run shows.** The observed total lowers leakage in every cell (outsider identified at 15–20 Mm³: 46 % with the exact total, 26 % now). Against the restated gate the display passes 4 of 8 cells and fails 4 (outsider identified +7.8 and +5.6, outsider knows whether pumped +13.3, insider identified +13.4, upper bounds). The excess comes from combining two differently rounded readings of one balance — the tank level after the season (rounded down) and the total (rounded half up) — by an observer who knows the starting stock exactly. With the starting stock known only to its 1 Mm³ level (a scratch analysis, not yet in the script), only insider identified at 15–20 Mm³ (+6.3) exceeds the margin. Most of the remaining identification comes from the few pump levels the private turn offers, not from the display (0.1 Mm³ grid sensitivity: outsider identified 2–4 %).
- **Stated openly.** When the paddy smallholders' wells are dry (all seasons below B_low, about a fifth at the low threshold), only two farms can pump, and each knows the other's pumping from the total and its own. This is the dilemma's own mechanism and breaks the three-contributor minimum of statistical disclosure control; R17's claim is worded accordingly in the debrief and the information sheet.
- **Open for the maintainer.** (a) Make the post-season tank level and the total consistent from one coarsening, or show only one of them; or (b) define the gate's observer as knowing the starting stock only to its observed level and add that observer to the script; and (c) confirm the 5-point margin. The display is not tuned to pass the gate until that choice is made.

## Amendment 2026-10-12: the private preview stops at the public limit (review E11)

- **Why.** The private turn previews each pump level's harvest and points. When the requested pumping exceeds the stock above the reserve, the wells are rationed, so before this change the previews at high levels moved with the true stock and a farm could read the exact stock above B_res from where its preview stopped rising, more than the tank's 1 Mm³ level shows.
- **Decision (implemented).** A level is previewed only up to `previewLimit` = (observed tank level − B_res), clipped at zero, which every farm already knows from the tank. With the others not pumping (the preview's stated assumption), no rationing is possible up to that limit whatever the true stock behind the observed level, so the preview depends on public information alone (property test `tests/test_preview.py`). Above it the private turn shows the level without a harvest or points and says that the water then depends on the stock and on what the others pump. The record carries `previewLimit` in `private.opened`; the balance harness's agents use only previewed levels and, wanting more, ask for their full well capacity.
- **What remains.** Rationing itself is a physical channel: in a rationed season the table pumps exactly B − B_res, so the post-season tank reads the reserve and the observed total gives the stock above it to 1 Mm³. That is what the tank and the total already show; the exact amount stays sealed.

## Sources (verified on Crossref or the publisher's page, 2026-10-11)

- Bigoni, M., & Suetens, S. (2012). Feedback and dynamics in public good experiments. *Journal of Economic Behavior & Organization* 82(1), 86–95. doi:10.1016/j.jebo.2011.12.013
- Cárdenas, J.-C., & Ostrom, E. (2004). What do people bring into the game? Experiments in the field about cooperation in the commons. *Agricultural Systems* 82(3), 307–326. doi:10.1016/j.agsy.2004.07.008; instructions in CAPRi Working Paper 32, IFPRI (hdl:10568/157403)
- Cárdenas, J.-C., Stranlund, J., & Willis, C. (2000). Local environmental control and institutional crowding-out. *World Development* 28(10), 1719–1733. doi:10.1016/S0305-750X(00)00055-3
- Dubois, D., Farolfi, S., Nguyen-Van, P., & Rouchier, J. (2020). Contrasting effects of information sharing on common-pool resource extraction behavior: experimental findings. *PLoS ONE* 15(10), e0240212. doi:10.1371/journal.pone.0240212
- Fiala, L., & Suetens, S. (2017). Transparency and cooperation in repeated dilemma games: a meta study. *Experimental Economics* 20(4), 755–771. doi:10.1007/s10683-017-9517-4
- Hundepool, A., Domingo-Ferrer, J., Franconi, L., Giessing, S., Lenz, R., Naylor, J., Schulte Nordholt, E., Seri, G., De Wolf, P.-P., Tent, R., Młodak, A., Gussenbauer, J., & Wilak, K. (2025). *Handbook on Statistical Disclosure Control*, 2nd ed. Centre of Excellence on SDC (STACE project). https://sdctools.github.io/HandbookSDC/
- Meinzen-Dick, R., Chaturvedi, R., Domènech, L., Ghate, R., Janssen, M. A., Rollins, N. D., & Sandeep, K. (2016). Games for groundwater governance: field experiments in Andhra Pradesh, India. *Ecology and Society* 21(3), 38. doi:10.5751/ES-08416-210338
- Sell, J., & Wilson, R. K. (1991). Levels of information and contributions to public goods. *Social Forces* 70(1), 107ff. doi:10.2307/2580064
