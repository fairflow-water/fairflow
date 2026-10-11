<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0010: The survival floor, what the collective score is, and two balance criteria restated

- Status: **accepted** 2026-10-11 by the maintainer ("proceed on the recommendation"), after two independent reviews (agronomy and game design; welfare economics and composite indicators).
- Amends §2.4, §2.5, R14 and §9.2 of the blueprint; follows ADR 0008, whose balance report left two §9.2 criteria failing.

## Context

The balance harness reported "crop failure" in 42 % of mixed games against a §9.2 band of 5–30 %, and the "no dominant lens" criterion failing because all-proportional tables always have the highest collective score. The reviews found:

1. **A boundary artefact.** The engine counted a low season at adequacy A ≤ 0.5. The sufficientarian lens gives each farm exactly 0.5 of its demand, and R15 states the paddy goal as "adequacy never < 0.5", so the lens built to guarantee survival raised the flag in every game.
2. **A label that overstates.** At A = 0.5 the FAO-33 relation still yields 45–53 % of the maximum in this basin. FAO-66 places wheat failure near 100–150 mm of available water (A ≈ 0.16–0.24 here), and the allocation is announced before the private turn, so a farm told it gets nothing would fallow rather than lose a crop (Steduto et al. 2012).
3. **The 5–30 % band has no source.** It measured how often the harness's random tables elected particular lenses, not basin science; at 400 games the mixed rate was 37.5 % (95 % interval 32.8–42.2 %), so the 42 % was partly sampling noise. The per-person lens, not the utilitarian one, caused most low seasons, and it also hits the citrus estate.
4. **The collective score is proportional by construction.** Its equity vertex is E_PJ, which the proportional lens makes 1; without pumping r₂ and r₃ barely vary between lenses, so the score is close to ∛E_PJ (OECD & JRC 2008; Munda & Nardo 2009 on compensability). The blueprint already says "the collective score is itself a lens". Comparing all-principled tables lens by lens therefore tests the score, not the vote. Measured faithfully — in mixed tables with a defecting seat, each replayed with every lens forced — no lens dominates.

## Decision

1. **Survival floor.** A season counts as low when A < 0.5, strictly; reaching the floor is survival. Two low seasons running are flagged as "below the survival floor two years running" (the record keeps the field name `cropFailure`); the flag marks a severe loss of livelihood, not agronomic crop failure.
2. **The collective score stays**, with its lens named and its limits stated in §2.5: close to ∛E_PJ without pumping; r₂ = min(F, 1) removes the efficiency gain only the utilitarian lens produces; the r₃ ramp lets equity partly offset depletion (a strong-sustainability reading would make S > 1 a constraint, Daly's ordering). The debrief adds the season score under each equity measure — E_PJ, and E_SE per claimant, per hectare and per person — so each yardstick is seen to favour the lens built on it (Sen's "equality of what?"). As used only after a per-player debrief (ADR 0004); as allocated always, with r₃ = 1 because an allocation alone never takes S above 1.
3. **§9.2 restated.**
   - *No dominant lens:* in mixed tables with at least one defecting seat, each replayed with every lens forced, no lens tops the collective score in more than 60 % of tables. The all-principled ranking is reported, not gated.
   - *Below the floor sometimes* (replaces "crop failure 5–30 % of mixed games"): some lens leaves a farm below the floor two years running in ≥ 5 % of its all-principled games and some lens in ≤ 5 %; the mixed-game rate is reported with its 95 % Wilson interval from at least 400 games.
   - *Human baselines:* the 55–75 % band cannot hold for proportional tables, which reach the score's maximum by construction; it is indicative only for the other lenses.
4. The harness's table mix is not tuned to pass any criterion.

## Consequences

- Engine: the strict floor test; the debrief scoreboard (`debrief.welfare`, recomputed by the audit). UI: the scoreboard table in S9. Tests cover the floor rule and the scoreboard's privacy.
- Measured with `analysis/balance.py` (Kelvara basin, ADR 0009 balance): see the measurements below.

## Measurements

From `packages/engine-py/analysis/balance_kelvara.json` (Kelvara basin with the ADR 0009 balance; 50 games per all-principled and selfish cell, 400 mixed games, and the 141 mixed tables with a defecting seat each replayed under all five lenses). All six v1.0 §9.2 criteria pass:

| Criterion | Result |
|---|---|
| No dominant lens (mixed tables with a defector, every lens forced) | per-person 38 %, strict egalitarian 27 %, sufficientarian 24 %, proportional 11 %, utilitarian 0 % of tables topped; all-principled tables: proportional tops 100 % (reported, not gated) |
| Below the floor sometimes (all-principled, by lens) | utilitarian 100 %, strict egalitarian 22 %, per-person 22 %, proportional 0 %, sufficientarian 0 %; mixed games 31.2 % (95 % interval 26.9–36.0 %, 400 games) |
| Dilemma | pumping pays in 94 % of deficit seasons above B_low; selfish tables past the suction limit by season 5 in 98 %; all-principled tables never below B_low |
| Lens matters, cooperation rewarded, goals attainable | pass, unchanged |

The strict floor test alone moved the mixed rate from 37.5 % to 31.2 %, as the review had computed independently.

## Sources

- Daly, H. E. (1990). Toward some operational principles of sustainable development. *Ecological Economics* 2, 1–6. doi:10.1016/0921-8009(90)90010-R
- Munda, G., & Nardo, M. (2009). Noncompensatory/nonlinear composite indicators for ranking countries: a defensible setting. *Applied Economics* 41, 1513–1523. doi:10.1080/00036840601019364
- OECD & JRC (2008). *Handbook on Constructing Composite Indicators: Methodology and User Guide*. OECD. doi:10.1787/9789264043466-en
- Steduto, P., Hsiao, T. C., Fereres, E., & Raes, D. (2012). *Crop yield response to water*. FAO Irrigation and Drainage Paper 66.
