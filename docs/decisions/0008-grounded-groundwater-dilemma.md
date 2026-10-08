<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0008: A grounded groundwater dilemma — expansion onto wells, lift energy, shallow wells that fail, lost baseflow

- Status: **accepted** 2026-10-08 by the maintainer ("adapt the blueprint realistically and create real but very grounded dilemma").
- Amends §2.2, §2.6, §4.3 and §9.2 of the blueprint; builds on ADR 0006 and ADR 0007.

## Context

With the corrected sustainability index and return-flow recharge of ADR 0007, the balance harness (`packages/engine-py/analysis/balance.py`) found that selfish tables barely drew the aquifer down: farms pumped only to fill the river's shortfall, a flat 2 Mm³ cap, and recharge from return flow refilled most of it. The §9.2 dilemma criterion — selfish tables reach the reserve by season 5 — had been tuned on the v1 reduction with no recharge at all.

The real world is not like that. Groundwater overdraft in irrigated semi-arid basins is severe and well documented: north-west India lost about 17.7 km³ a year in 2002–2008 (Rodell, Velicogna & Famiglietti 2009); 330 km³ of the High Plains aquifer has been depleted (Scanlon et al. 2012); water tables fall faster than 0.5 m a year in 24 % of arid-zone aquifers (Jasechko et al. 2024). What the model lacked were the mechanisms that make it so:

1. **Expansion onto groundwater is the driver.** India's share of irrigated area served by groundwater rose from 29 % in 1951 to 62 % in 2003 while surface irrigation stopped growing (Siebert et al. 2010); efficiency gains are half lost to expansion (Fishman, Devineni & Raman 2015).
2. **Wells supply a large share of irrigation**: 38 % of the world's irrigated area, 57 % in South Asia, 43 % of consumptive irrigation use (Siebert et al. 2010).
3. **What hurts first is shallow wells failing.** Centrifugal pumps cannot lift water from below about 8 m; where the water table passes that depth, smallholders lose access, poverty is 9–10 % higher and disputes rise (Sekhri 2014). Across 39 million wells, 6–20 % are no more than 5 m deeper than the water table (Jasechko & Perrone 2021).
4. **Lift energy rises only in proportion to the head** (E = ρgH/η); smallholder pump sets are inefficient, 25–30 % on average and 21–24 % in audits, against 40–45 % for good sets (Singh et al. 2023).
5. **Pumping captures streamflow.** In long-developed systems about 85 % of pumping is captured, mostly as streamflow depletion (Konikow & Leake 2014; Barlow & Leake 2012); environmental-flow limits are reached in many pumped watersheds before storage losses are large (de Graaf et al. 2019).

## Decision

1. **One round is one irrigation year.** The demands are annual depths; the drawdown a table can cause in five or six years is of the order of the "rapid" rates Jasechko et al. (2024) report.
2. **The aquifer's storage–head link.** Storage per metre of water-table change = area × specific yield ≈ 50 km² × 0.10 = 5 Mm³ per m (specific yield of alluvium 0.02–0.27, Johnson 1967; 0.10 a convention). The aquifer is full (20 Mm³) at 7 m depth; the low threshold B_low = 15 Mm³ is 8 m, the suction limit of shallow pumps (Sekhri 2014); the reserve B_res = 10 Mm³ is 9 m, where pumping stops. The 1 m of headroom between full and the suction limit is a convention inside Jasechko & Perrone's finding that 6–20 % of wells sit within 5 m of the water table. Natural recharge, 1 Mm³ a year, is 20 mm over 50 km², within the semi-arid range 0.2–35 mm (Scanlon et al. 2006).
3. **Well capacity is a share of demand** and grows with the irrigated area (Expand adds wells):

   | Pump capacity share of demand | 0.5 (convention within 0.38–0.57) |
   |---|---|

   The flat cap remains for scenarios without a share.
4. **Pump cost is lift energy.** c = factor × (costBase + costSlope·(1 − B/B₀)), linear in the head, with costSlope/costBase = B₀ / (storage per metre × head at B₀) = 20 / (5 × (7 + 3)) for a 7 m depth plus 3 m of well drawdown and delivery head (convention). The factor is each scheme's pump-set inefficiency relative to the best set, η_ref/η_i: estate 1.0 (η ≈ 0.45), paddy smallholders 1.8 (η ≈ 0.25), family wheat farms 1.5 (η ≈ 0.30) (Singh et al. 2023). It applies always; the seat multipliers of §2.2 are set to 1.
5. **Shallow wells fail.** The paddy smallholders' wells deliver nothing once the observed level is at or below B_low (8 m). The family wheat farms' wells reach 10 m and the estate's submersible pumps deeper, so neither fails above the reserve.
6. **Baseflow loss starts at the first drawdown.** Next season's inflow falls by κ(B₀ − B), κ = 0.1 (convention), in place of the §2.2 rule that began only below B_low.
7. **§9.2 dilemma criterion, restated for a basin with recharge.** Pumping is individually profitable in at least 80 % of deficit seasons while B > B_low; selfish tables drive the water table below the smallholders' suction limit by season 5 in at least 80 % of games; all-principled tables never do. The goal criterion is judged per lens: every R15 goal is met in at least 50 % of all-principled games under at least two lenses, and some lens meets all goals together in at least half its games.

## Consequences

- Measured with the balance harness (`analysis/balance_kelvara.json`, 50 games per cell, Kelvara basin as above):
  - **passed** — lens matters (dry-year E_PJ range 0.87; one scheme's allocation varies by 98 % of its demand across lenses); cooperation rewarded (every all-principled table ends with B = B₀); dilemma (pumping pays in 96 % of deficit seasons above B_low; selfish tables pass the suction limit by season 5 in 82 % of games; all-principled tables never fall below B_low); goals (each goal is met with certainty under two or three lenses; under the proportional lens the estate meets its goal in 58 % of games and the paddy and wheat farms in all);
  - **failed** — "no dominant lens": all-proportional tables always have the highest collective score, because the score's equity vertex is proportional equity (§2.5 says the scoreboard is itself a lens); measuring it as §9.2 intends needs mixed tables and is left to the maintainer; "crop failure 5–30 % of mixed games": 42 %, mostly where a value-maximising or per-person lens leaves the wheat farms without water. Neither is tuned away here.
- The independent reference implementation (`analysis/reference_model.py`) gives the same shape on a fixed deck: under full selfish pumping the paddy wells fail in round 2 and the aquifer settles near 13–15 Mm³ with up to 0.8 Mm³ of baseflow lost a year; under cooperation the aquifer stays full.
- The dilemma now bites where it does in the field: the estate's and the family farms' pumping dries the smallholders' wells and takes baseflow from the river that every farm shares next season.
- Engine (Python and the TypeScript mirror), schema, registry and golden vectors change together; the §3 worked examples are regenerated by the independent reference implementation.

## Sources

- Barlow, P. M., & Leake, S. A. (2012). *Streamflow depletion by wells*. USGS Circular 1376. doi:10.3133/cir1376
- de Graaf, I. E. M., Gleeson, T., van Beek, L. P. H., Sutanudjaja, E. H., & Bierkens, M. F. P. (2019). Environmental flow limits to global groundwater pumping. *Nature* 574, 90–94. doi:10.1038/s41586-019-1594-4
- Fishman, R., Devineni, N., & Raman, S. (2015). Can improved agricultural water use efficiency save India's groundwater? *Environmental Research Letters* 10, 084022. doi:10.1088/1748-9326/10/8/084022
- Jasechko, S., & Perrone, D. (2021). Global groundwater wells at risk of running dry. *Science* 372, 418–421. doi:10.1126/science.abc2755
- Jasechko, S., et al. (2024). Rapid groundwater decline and some cases of recovery in aquifers globally. *Nature* 625, 715–721. doi:10.1038/s41586-023-06879-8
- Johnson, A. I. (1967). *Specific yield: compilation of specific yields for various materials*. USGS Water-Supply Paper 1662-D. doi:10.3133/wsp1662D
- Konikow, L. F., & Leake, S. A. (2014). Depletion and capture: revisiting "The source of water derived from wells". *Groundwater* 52(S1), 100–111. doi:10.1111/gwat.12204
- Rodell, M., Velicogna, I., & Famiglietti, J. S. (2009). Satellite-based estimates of groundwater depletion in India. *Nature* 460, 999–1002. doi:10.1038/nature08238
- Scanlon, B. R., et al. (2006). Global synthesis of groundwater recharge in semiarid and arid regions. *Hydrological Processes* 20, 3335–3370. doi:10.1002/hyp.6335
- Scanlon, B. R., et al. (2012). Groundwater depletion and sustainability of irrigation in the US High Plains and Central Valley. *PNAS* 109, 9320–9325. doi:10.1073/pnas.1200311109
- Sekhri, S. (2014). Wells, water, and welfare: the impact of access to groundwater on rural poverty and conflict. *American Economic Journal: Applied Economics* 6(3), 76–102. doi:10.1257/app.6.3.76
- Siebert, S., et al. (2010). Groundwater use for irrigation – a global inventory. *Hydrology and Earth System Sciences* 14, 1863–1880. doi:10.5194/hess-14-1863-2010
- Singh, K., Jhorar, R. K., et al. (2023). Energy conservation prospects in water intensive paddy-wheat cropping system for groundwater pumping in the semi-arid region of Haryana. *PeerJ* 11, e14815. doi:10.7717/peerj.14815
