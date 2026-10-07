<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0006: Aquifer capacity (rejected recharge) and a floor on the pump cost

- Status: **accepted** 2026-10-07 by the maintainer ("continue as recommended, but also address this effectively").
- Amends §2.2 (the pump cost) and §2.6 (the aquifer balance) of the blueprint.

## Context

The first real-browser game (2026-10-07) exposed two linked gaps in blueprint v3.1.

1. **The pump cost turns negative.** §2.2 sets c = 2 + 6(1 − Bₜ/B₀). With B₀ = 20 this is 0 at B = 26.7 and −3.4 at B = 38 (computed in Python). A negative cost pays a farm to pump.
   - Every cost the blueprint quotes is at or below B₀: "2.0 at B₀, 3.8 at 14, 5.6 at 8 and 6.5 at 5" (§9.2). That is the range in which the dilemma was calibrated. Above B₀ the formula is untested extrapolation.
2. **The aquifer has no capacity.** The §2.6 balance has a floor (B_res) but no ceiling. Return flows and r₀ add about 5 Mm³ a season, so a table that holds back on pumping watches the aquifer fill without limit. The engine-played fixture game reached 38 Mm³ in five seasons.
   - Real aquifers cannot do this. Under natural conditions an aquifer is in approximate dynamic equilibrium: recharge is balanced by natural discharge to springs, rivers and evapotranspiration (Theis 1940; Bredehoeft, Papadopulos & Cooper 1982).
   - When the aquifer is full, further recharge is rejected and leaves as discharge. Theis (1940) calls this rejected recharge.
   - Pumping is supplied by storage depletion and by capture: increased recharge and decreased discharge (Konikow & Leake 2014).
   - The blueprint already grounds B_res in this literature ("water-budget myth: Alley & Leake 2004").

## Decision

1. **Pump cost floor.** c = costBase + costSlope·max(0, 1 − Bₜ/B₀), times the seat multiplier once Bₜ < B_low.
   - The cost never falls below costBase, the blueprint's cost at B₀. Below B₀ nothing changes, so every §3 fixture and the §9.2 dilemma are untouched.
   - Pumping costs at least the fixed share of lifting and delivering water, however shallow the water table. The floor needs no new parameter.
2. **Aquifer capacity B_max.** B_{t+1} = min(B_max, max(B_res, Bₜ + surplus + r₀ + Σ(1 − βᵢ)Wᵢ − ΣPᵢ)).
   - The excess over B_max is the season's **spill**, the rejected recharge.
3. **Default capacity: B_max = B₀.**

   | Aquifer capacity B_max | 20 Mm³ = B₀ (admin-settable per scenario) |
   |---|---|

   - The game starts from the predevelopment equilibrium that capture theory takes as its baseline: the aquifer is full, and what is pumped comes from storage or capture.
   - Recharge refills it up to B₀ and no further. This is also the shallowest level at which the blueprint calibrates the pump cost, so with the default the cost formula is only ever used where it was calibrated.
   - A scenario may set `basin.aquifer.capacity` above `initial`, to start part-full. When omitted, the loader uses `initial`. A capacity below `initial`, or at or below `lowThreshold`, is refused at load.
   - The engine accepts no capacity (unbounded) only to reproduce the blueprint §3 fixtures, which isolate one term each. No shipped scenario uses that.
4. **Where the spill goes.** The spill leaves the basin as natural discharge. It is **not** added to the river.
   - The climate cards' inflows are absolute values calibrated on a basin with a healthy aquifer (§2.2). They already contain the normal baseflow, which is why the GW–SW coupling only subtracts while B < B_low. Adding the spill back would count it twice.
   - Routing part of the spill to the next season's inflow is a calibration question for the balance harness, not a v1.0 default.
5. **Disclosure (ADR 0004).**
   - The spill is computed on actual use (return flows depend on each farm's pumping), so it is **sealed** until the debrief, like `stockNext`.
   - The table sees `aquiferFull`: whether the observed level has reached the observed capacity. That follows from the observed level the table already sees, so it discloses nothing new.
   - ADR 0004's leakage measurements sampled stock between B_low and B₀, which this decision does not change. At the capacity, the observed level stops moving, which can only reveal less.
   - Measured (`analysis/privacy_leakage_capacity.md`, same seed and seasons as ADR 0004): for the implemented display at normal stock, outsider identified 9 % (8–11) against 10 % (9–12) before, outsider knows whether pumped 17 % (15–19) against 18 % (16–21), insider identified 41 % (38–43) against 41 % (39–44), insider knows whether pumped 66 % (63–68) against 68 % (65–70). Low stock is unchanged, as expected. No figure rises.
6. **Debrief value.** "Holding back filled the aquifer; beyond full, the water left the basin" is the water-budget myth enacted, and the spill gives the debrief its number.

## Consequences

- Engine (Python, authoritative) and the TypeScript mirror change together. Golden vectors are regenerated: half the random cases have a capacity, half none. A property test checks that B ≤ B_max and that the balance closes with the spill (B_{t+1} + spill = unbounded balance). Another checks that the cost never falls below costBase.
- The parameter registry gains `basin.aquifer.capacity`, quoting this record.
- The balance harness (ADR 0005) reports the share of seasons at capacity and the spill per game, so any calibration of B_max is measured rather than guessed.

## Sources

- Theis, C. V. (1940). The source of water derived from wells: essential factors controlling the response of an aquifer to development. *Civil Engineering* 10(5), 277–280.
- Bredehoeft, J. D., Papadopulos, S. S., & Cooper, H. H. (1982). Groundwater: the water-budget myth. In *Scientific Basis of Water-Resource Management*, Studies in Geophysics, National Academy Press, 51–57.
- Alley, W. M., & Leake, S. A. (2004). The journey from safe yield to sustainability. *Ground Water* 42(1), 12–16.
- Konikow, L. F., & Leake, S. A. (2014). Depletion and capture: revisiting "The source of water derived from wells". *Groundwater* 52(S1), 100–111.
