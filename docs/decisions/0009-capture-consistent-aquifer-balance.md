<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0009: A capture-consistent river–aquifer balance, and where the spill goes

- Status: **accepted** 2026-10-11 by the maintainer ("proceed on the recommendation"), after an independent hydrogeology review of review findings B20 and E11.
- Amends §2.5 (S), §2.6 and ADR 0006 point 4; refines ADR 0008 point 6.

## Context

ADR 0008 made pumping take baseflow from the river from the first drawdown: next season's inflow falls by κ(B₀ − B). The aquifer balance, however, still credited the full natural recharge r₀ to storage in every season. At full storage that is right only because the recharge is rejected and leaves as spill. Below full it counts the same water twice: the river still receives the baseflow the cards contain, less κ(B₀ − B), and the aquifer keeps all of r₀ as well. In nature the two are one flow. Before development an aquifer is in approximate dynamic equilibrium, its recharge balanced by natural discharge; pumping is supplied by storage loss and by capture, increased recharge or decreased discharge (Theis 1940; Konikow & Leake 2014), and most capture is streamflow depletion (Barlow & Leake 2012).

The review also found that ADR 0006's wording, that the spill "leaves the basin as natural discharge", was not hydrology. Theis (1940) describes rejected recharge leaving through springs, seepage to streams and evapotranspiration: water that reaches the river, not water that vanishes.

## Decision

1. **Natural gain.** With the baseflow coupling of ADR 0008, natural recharge r₀ is balanced at full storage by natural discharge to the river, which the climate cards' inflows already contain. Below full the discharge falls by κ(B₀ − B), and that is what the aquifer gains:

   G(B) = min(r₀, κ·max(0, B₀ − B)), B the observed level (ADR 0004).

   B_{t+1} = min(B_max, max(B_res, B_t + surplus + G(B_t) + ρΣ(1 − βᵢ)Wᵢ − ΣPᵢ)), and next season's inflow falls by min(r₀, κ·max(0, B₀ − B_{t+1})). The river loses in each season exactly what the aquifer gains in it. Scenarios without the coupling keep the §2.6 rule, G = r₀.
2. **Sustainability.** S = (ΣβᵢWᵢ + (1 − ρ)Σ(1 − βᵢ)Wᵢ) / (AWₜ + G(Bₜ)); the identity AWₜ + G − ΣβᵢWᵢ − (1 − ρ)Σ(1 − βᵢ)Wᵢ = ΔB + spill still holds, so S > 1 exactly when storage falls.
3. **Where the spill goes** (replaces ADR 0006 point 4). The spill is rejected recharge (Theis 1940): this season's river surplus and the share ρ of return flow that a full aquifer cannot store. It leaves the aquifer in the same season as discharge to the river below the schemes' off-takes, springs and evapotranspiration. It reaches the river only below every off-take, so no scheme can divert it this season, and one round is one irrigation year with no storage lag, so none of it is carried into the next season. The model records it and the debrief reports it; it is added to no scheme's inflow. Pumping from a full aquifer first reduces the spill, so it first depletes the river downstream of the schemes; the game has no downstream claimant, so that depletion is reported, not scored.

## Consequences

- Moderate pumping from a full aquifer is no longer free: it draws down storage, which then gains G while the river loses the same amount the next season. This is the capture behaviour the literature describes, and it removes the water-budget myth the earlier balance enacted (Bredehoeft, Papadopulos & Cooper 1982).
- Engine (Python and the TypeScript mirror), golden vectors and the §3 dynamic fixtures change; the reference implementation (`analysis/reference_model.py`) applies the same rule from this text. A property test checks that the aquifer's natural gain equals the river's loss and that the balance closes.
- The balance harness was re-run (`analysis/balance_kelvara.json`, 50 games per cell): the dilemma is stronger, not weaker — selfish tables pass the smallholders' suction limit by season 5 in 98 % of games (82 % before), all-principled tables never fall below B_low, and pumping still pays in 96 % of deficit seasons above B_low. The other §9.2 results are unchanged.

## Sources

- Theis, C. V. (1940). The source of water derived from wells: essential factors controlling the response of an aquifer to development. *Civil Engineering* 10(5), 277–280 (USGS Ground Water Note 34 reprint).
- Konikow, L. F., & Leake, S. A. (2014). Depletion and capture: revisiting "The source of water derived from wells". *Groundwater* 52(S1), 100–111. doi:10.1111/gwat.12204
- Barlow, P. M., & Leake, S. A. (2012). *Streamflow depletion by wells*. USGS Circular 1376. doi:10.3133/cir1376
- Bredehoeft, J. D., Papadopulos, S. S., & Cooper, H. H. (1982). Groundwater: the water-budget myth. In *Scientific Basis of Water-Resource Management*, Studies in Geophysics, National Academy Press, 51–57.
