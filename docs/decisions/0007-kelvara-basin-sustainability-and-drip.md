<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0007: The Kelvara basin, a sustainability index that closes the water balance, and Drip by irrigation method

- Status: **accepted** 2026-10-08 by the maintainer ("follow your recommendations and proceed").
- Amends §2.1, §2.2, §2.5, §3, §4.3 and §11 of the blueprint. Follows the correctness review of 2026-10-08 (`docs/reviews/2026-10-08-correctness-review.md`, findings B4, B5, B7, B8, B9, B17, B23).

## Context

The review found the default basin stitched together from several real places and papers: households and employees from one paper's table, a dam buffer from one Kenyan scheme, a groundwater draft ratio from one Indian block, labour from another country's statistics. The units of "people" were mixed, one crop depth was outside its typical range, two Kᵧ values were attributed to sources that do not give them, the sustainability index contradicted the aquifer balance, and Drip changed water consumption in directions the irrigation literature does not support. A case built that way is neither a real place nor a consistent hypothesis.

## Decision

1. **One hypothetical basin.** The default scenario is the **Kelvara basin**, a hypothetical semi-arid river basin. Its name matches no river or place found in OpenStreetMap, GeoNames or Wikipedia (checked 2026-10-08). Every number is a typical value from the literature, cited as typical, or a labelled teaching convention; none is a measurement of a real place. Real cases (named schemes, laws, villages) appear only as labelled real-world examples, for example on lens-card backs, never as the source of a scenario number. The values, their sources and every derived value are produced by `packages/engine-py/analysis/kelvara_basin.py`.

   | Scheme (seat) | Crop, method | Area | Gross depth | β | Yield | Kᵧ | Price (wheat = 1) |
   |---|---|---|---|---|---|---|---|
   | Upper Citrus Estate (1) | citrus, drip | 625 ha | 1,000 mm | 0.90 | 16 t/ha | 0.95 | 1.71 |
   | Midstream Paddy Cooperative (2) | flooded rice | 900 ha | 1,000 mm | 0.60 | 5.0 t/ha | 1.1 (assumed) | 1.99 |
   | Tail-end Wheat Farms (3) | winter wheat, sprinkler | 400 ha | 850 mm | 0.75 | 5.0 t/ha | 1.05 | 1.00 |

   River and reserve keep their values (inflow 22 / 17 / 12 Mm³, reserve 2, recharge 1; the aquifer's thresholds are set in ADR 0008): each lies in its typical range or is a labelled convention (sources in the script).

2. **People in one unit.** Nᵢ counts people whose livelihood depends on the scheme's water: (farm households + full-time hired workers) × a household size of 5 (UN DESA household-size median 4.65, rounded), hired labour in Eurostat annual work units of 1,800 hours: 634 / 5,225 / 504 people. Labour coefficients read in full from official sources (Junta de Andalucía orange cost study 2022/23; India DES Cost of Cultivation medians); family labour is counted through households, so only hired labour is added.

3. **Harvest value.** Utilitarian lenses and livelihood points add harvest **value**, pᵢYᵢ, with typical producer-price ratios relative to wheat (FAOSTAT producer prices 2019–2023, medians across semi-arid countries; the ratios vary one- to four-fold between countries, which the game states). Adding tonnes of fruit, rice and wheat as if alike has no meaning.

4. **Where return flow goes.** Of the non-consumed water (1 − βᵢ)Wᵢ, a share ρ recharges the shared aquifer; the rest returns through drains and baseflow to the river below the schemes' off-takes and leaves the basin's shared stores.

   | Return-flow recharge share ρ | 0.6 (convention within 0.4–0.75) |
   |---|---|

   Supporting range: in the Indus, 0.43 of non-consumed field water reaches groundwater, 0.71 with canal seepage (Karimi et al. 2013); India's groundwater-estimation norms imply about 0.5–0.75 where the water table is shallower than 25 m (GEC-2015). No source states a single typical value, so 0.6 is a labelled convention.

5. **Actions that make physical sense.** A scheme may play only the actions listed for it (`actions` in the scenario): Orchard and Drip are not offered to an estate that is already an orchard on drip; Drip is not offered to flooded paddy, for which there is no constant-yield basis (Tuong, Bouman & Mortimer 2005).

6. **Drip.** Switching a scheme to drip at constant area and yield changes consumption little and removes most of the recoverable return flow (Perry 2007; Ward & Pulido-Velazquez 2008; Grafton et al. 2018). Soil-evaporation savings make consumption slightly lower (FAO-56 wetted fraction 1.0 for sprinkler against 0.3–0.4 for drip; field ET 4–6 % lower, Yang et al. 2020). From t+1:

   C′ = c_drip · βᵢ · Dᵢ, D′ = C′ / β_drip, β′ = β_drip, K unchanged,

   | Drip consumption factor c_drip | 0.95 (convention within the 0–6 % field range) |
   |---|---|

   with β_drip = 0.90 (§4.3). For the wheat farms this cuts diversion by 21 % and return flow by 68 % at the same yield. Consumption then rises only through the engine itself (a short season now covers more of the farm's need) or through Expand — the efficiency paradox, carried by the actions that cause it (Contor & Taylor 2013; Berbel et al. 2018).

7. **Sustainability index.** S = (Σ βᵢWᵢ + (1 − ρ) Σ (1 − βᵢ)Wᵢ) / (AWₜ + r₀): what leaves the basin's shared stores — consumption plus the returns to the river below the off-takes — over the renewable water available after the reserve. Consumption over availability net of the environmental requirement is the structure of blue-water scarcity (Hoekstra et al. 2012); return flows are not added as supply because consumption already excludes them. The previous denominator β*·AWₜ + r₀ removed the return flow a second time, so S could read "far above renewable supply" while the aquifer was full and spilling. With the new S, in this one-store basin,

   AWₜ + r₀ − Σ βᵢWᵢ − (1 − ρ) Σ (1 − βᵢ)Wᵢ = ΔB + spill,

   so S > 1 exactly when aquifer storage falls: the depletion test of Bredehoeft (2002) and Konikow & Leake (2014). No lens alone can push S above 1; only pumping can. The band edge 1.15 has no literature source and is labelled a game convention; band words: "within renewable supply", "drawing on stored groundwater", "mining stored groundwater fast".

8. **Orchard.** Playing Orchard switches a scheme to the basin's orchard crop (the estate's citrus: 1,000 mm on drip, i.e. 900 mm consumed; 16 t/ha, Kᵧ 0.95, value 1.71) at the scheme's own area and irrigation method. The tree consumes what it consumes, so the diversion is recomputed for the scheme's own β: D = area × 1,000 mm × 0.90 / βᵢ. The previous rule, D × 1.3 and p × 2, was written when every price was 1; with crop values it would make paddy worth more than citrus.

9. **Calibrating the conventions.** Aquifer storage and thresholds, the pump-cost curve, the seat multipliers, the pump cap, action costs, goal thresholds and the r₃ ramp are teaching conventions. They are calibrated against the §9.2 balance criteria with `packages/engine-py/analysis/balance.py` and `calibrate.py`, holding every sourced value fixed, and the chosen values and the criteria they meet are recorded here.

## Consequences

- The §3 worked examples are regenerated by an independent reference implementation (written from §2, not importing the engine), so the engine tests still compare two implementations.
- With the corrected S the shipped basin depletes only slowly (dry, dry, normal with every farm pumping 2: 20 → 19.2 → 18.4 → 19.0 Mm³ on the previous basin). The pump costs, action costs, goal thresholds, the r₃ ramp and the 1.15 edge are conventions; they are calibrated against the §9.2 balance targets in the balance harness and reported, not tuned silently.
- The registry replaces `actions.drip.demandFactor` with `actions.drip.consumptionFactor`, quoting this record.

## Sources

- Berbel, J., Gutiérrez-Martín, C., & Expósito, A. (2018). Impacts of irrigation efficiency improvement on water use, water consumption and response to water price at field level. *Agricultural Water Management* 203, 423–429. doi:10.1016/j.agwat.2018.02.026
- Bredehoeft, J. D. (2002). The water budget myth revisited: why hydrogeologists model. *Ground Water* 40(4), 340–345. doi:10.1111/j.1745-6584.2002.tb02511.x
- Contor, B. A., & Taylor, R. G. (2013). Why improving irrigation efficiency increases total volume of consumptive use. *Irrigation and Drainage* 62(3), 273–280. doi:10.1002/ird.1717
- Grafton, R. Q., et al. (2018). The paradox of irrigation efficiency. *Science* 361(6404), 748–750. doi:10.1126/science.aat9314
- Karimi, P., Bastiaanssen, W. G. M., Molden, D., & Cheema, M. J. M. (2013). Basin-wide water accounting based on remote sensing data: an application for the Indus Basin. *Hydrology and Earth System Sciences* 17, 2473–2486. doi:10.5194/hess-17-2473-2013
- Central Ground Water Board (2017). *Report of the Ground Water Resource Estimation Committee (GEC-2015)*, Table 6. Government of India.
- Hoekstra, A. Y., Mekonnen, M. M., Chapagain, A. K., Mathews, R. E., & Richter, B. D. (2012). Global monthly water scarcity: blue water footprints versus blue water availability. *PLoS ONE* 7(2), e32688. doi:10.1371/journal.pone.0032688
- Konikow, L. F., & Leake, S. A. (2014). Depletion and capture: revisiting "The source of water derived from wells". *Groundwater* 52(S1), 100–111. doi:10.1111/gwat.12204
- Perry, C. (2007). Efficient irrigation; inefficient communication; flawed recommendations. *Irrigation and Drainage* 56(4), 367–378. doi:10.1002/ird.323
- Tuong, T. P., Bouman, B. A. M., & Mortimer, M. (2005). More rice, less water: integrated approaches for increasing water productivity in irrigated rice-based systems in Asia. *Plant Production Science* 8(3), 231–241. doi:10.1626/pps.8.231
- Ward, F. A., & Pulido-Velazquez, M. (2008). Water conservation in irrigation can increase water use. *PNAS* 105(47), 18215–18220. doi:10.1073/pnas.0805554105
- Yang, D., Li, S., Kang, S., Du, T., et al. (2020). Effect of drip irrigation on wheat evapotranspiration, soil evaporation and transpiration in Northwest China. *Agricultural Water Management* 232, 106001. doi:10.1016/j.agwat.2020.106001
- Value and range sources for every basin number: `packages/engine-py/analysis/kelvara_basin.py`.
