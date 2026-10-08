<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Correctness review, 2026-10-08

A full review of the repository for scientific and factual correctness, in four independent parts: references; blueprint
equations and claims; the engine against its documentation; and every statement a user reads. Numeric checks were run in
Python (independent re-implementations and the engine), never by hand. Findings marked *reproduced* were re-run by the
maintainer's assistant before this record was written. Each item has an id so that fixes can cite it.

Status legend: **fix** = clear error, corrected without a decision; **decide** = needs the maintainer's scientific
judgement; **source** = needs a source only the authors have.

## A. Engine (Python authoritative, TypeScript mirror)

| id | finding | status |
|---|---|---|
| E1 | The verdict and the debrief lens rows use the scenario's base lens parameters, not the floor rule the table voted (`record.py` verdict call, previews, debrief rows). In a floor-shortfall season "sufficientarian" can never be named: after Orchard on A in a dry year, a sufficientarian vote with the CEL floor rule is reported as "satisfied: proportional", with CEA as "talmud". *Reproduced.* Ties between identical ideal allocations also go to card order rather than the voted lens. | fix |
| E2 | `max(B_res, ·)` in `_unbounded_stock` creates water when the stock starts below the reserve, and the loader allows initial < reserve and capacity < reserve: initial 4, reserve 5, no flows → 5. *Reproduced.* The phantom water also appears as spill. With valid scenarios both balances close to rounding (3,000 random seasons). | fix |
| E3 | `basin.inflow.dryDrift`, `aquifer.surplusRecharge` and `aquifer.returnFlows` are validated but never used in play. | fix (reject non-default values until implemented) |
| E4 | κ = 0 (allowed by the schema) makes the capability lens divide by a zero weight sum: Python raises (a season cannot open), TypeScript returns NaN. | fix |
| E5 | The utilitarian optimum is not unique when schemes tie in marginal value; the Python MILP and the TypeScript enumeration then return different allocations of equal value (22 of 400 random tied cases). No tie-break is specified. | decide (tie-break rule), then fix |
| E6 | `pwf_ede` underflows to 0 for γ ≳ 200; `welfare()` has no γ = ∞ branch (NaN); precision loss near γ = 1. | fix |
| E7 | Unvalidated scoring inputs: survivalFloor ∈ {0, 1}, welfareSupplyFloor = 0, r3Ramp = 0, n = 1, Kᵧ > 2 (negative harvest at the floor). | fix (load-time checks) |
| E8 | Double rounding in Talmud and sufficientarian; ΣQ can miss the estate by up to n·1e-6 and the residual is not booked. | fix |
| E9 | `game.ended.collectiveScore` is public, unrounded, and equals the sealed triangle score in a one-season game; `project()` docstring overstates what opens after the debrief. | fix |
| E10 | Season points shown (`dL`) exclude the action cost that is charged to the running total: preview "+36", reveal "+46 this season; 36 in total". | fix |
| E11 | The private-turn preview, when pump rationing binds, reveals the exact stock above the reserve (ADR 0004 aims at the coarse level). | decide |

## B. Blueprint and decision records

| id | finding | status |
|---|---|---|
| B1 | §2.3 utilitarian "greedy by marginal value" is not optimal: the production function is non-concave when Kᵧ > 1 (counterexample found). The engine correctly uses a MILP; the text must say so. | fix |
| B2 | §2.7 "EWF = 1 − G\*(s)" uses the notation of the corrected Gini, but §3.1 and the engine use the uncorrected Gini. | fix (notation) |
| B3 | §3.4 "every other principle ranks it [strict utilitarian, dry year] worst" is false: only PWF₃ and CWF do; EWF ranks capability lower; SWF = 0 for six lenses. | fix |
| B4 | §2.5 statements about S are false under the shipped β set: S crosses 1 at Σβᵢ·Pᵢ = r₀, not ΣP = r₀; a lens alone (utilitarian, dry, no pumping) gives S = 1.013; "wet year S < 1 by construction" holds only without pumping. | fix |
| B5 | §2.5 r₃ ramp calibration ("S ≈ 1.6 scores 0, S = 1.3 scores 0.5") holds only for β = 1, r₀ = 0; with the shipped β the dry-year maximum is S = 1.556, so r₃ never reaches 0. | decide (recalibrate, balance harness) |
| B6 | §2.5 "616.6 t/Mm³" is per m³ diverted; the dial is per m³ consumed (847.1). | fix |
| B7 | §2.2: paddy "1,000 households × 0.9 ha" contradicts N_B = 2,000 households. N_C = 42 households has no source. People units are mixed (employees vs households) and no screen states them. | source |
| B8 | Drip (D × 0.8, β → 0.90) cuts consumption for A (−20 %) and C (−4 %) at constant yield, the "efficiency frees water" effect §2.2 rejects; raises it 20 % for B with no agronomic basis. | decide |
| B9 | Kᵧ sources: FAO-66 Table 1 has no citrus; its wheat values are 1.15 spring / 1.05 winter; citrus 0.8–1.1 is FAO-33. Bouman & Tuong (2001) reports no Kᵧ for rice. | fix (re-attribute; rice 1.1 "assumed") |
| B10 | §11 "1 − CV is unbounded below" is false at fixed n: the minimum is 1 − √(n−1). Engine docstring repeats it. | fix |
| B11 | "empirical ε in 1–2" refers to the elasticity of marginal utility of consumption; elicited inequality aversion is often lower; the default γ = 3 is outside the cited range and must be called a reference value. | fix (wording) |
| B12 | §2.3 "Talmud equals equal sacrifice when no half-claim is exhausted" is incomplete (also needs AW ≥ ½ΣD and the equal loss ≤ min Dᵢ/2). | fix |
| B13 | §3.4 pump profitability claims are overstated (B below 50 % adequacy; A's break-even at B = 5.33). | fix |
| B14 | §2.2 reserve "between Tennant's 10 % and Q95" is undefined (Q95 is a percentile); R = 2 is below 10 % of wet inflow. | fix (wording) |
| B15 | §2.2 inflow deck CV (0.21) is low for semi-arid runoff; "matches Balotra draft" compares a surface ratio with a groundwater ratio. | fix (wording) |
| B16 | "~1.2 years of inflow" should be "~1.2 seasons of normal inflow". Also in `default-basin.json`. | fix |
| B17 | Sustainability bands: Gleeson et al. (2012) define a footprint ratio with no 1.15 threshold; the 1.15 edge is a game convention. | fix (wording) |
| B18 | The blueprint body predates accepted ADRs 0004 and 0006 (pump cost floor and coarse level, B_max and spill, R17 dials). ADR 0006 cites "§9.2" for a list that is in §3.4. | fix |
| B19 | ADR 0004 Wilson intervals treat the three schemes of a season as independent (n = 1,200 instead of 400 clusters); intervals are too narrow. | fix (cluster bootstrap, re-run) |
| B20 | ADR 0006 "spill leaves the basin as natural discharge" is a modelling convention, not hydrology; the surplus and return-flow part of the spill is this season's water. | fix (wording) |
| B21 | Minor: Dworkin 1981 does not ground equal shares; "no legal anchor" for capability is overstated; Mwea return-flow analogy is loose; Bₜ vs Bₜ₊₁ notation; "the rebound" is partial in the Drip-then-Expand fixture; Y_B = 2,492.5 rounding. | fix |
| B22 | Case studies in §5.3 lack references in §12.4. | source |
| B23 | Sustainability band text in play ("far above renewable supply") can coincide with a full, spilling aquifer: S does not credit return-flow recharge that the aquifer balance credits. | decide |

## C. References

| id | finding | status |
|---|---|---|
| C1 | "Makale et al. 2024" (blueprint M4): first author is Constantine; Constantine et al. 2023, *Pest Manag. Sci.* 79(11): 4343–4356, doi:10.1002/ps.7638 (14 % yield loss supports Y × 0.86). | fix |
| C2 | "Gleeson et al. 2020 *Nat. Sustain.*" → *Annu. Rev. Earth Planet. Sci.* 48: 431–463, doi:10.1146/annurev-earth-071719-055251. | fix |
| C3 | "Jarke-Neuert 2025 *JESA*" → 2023, *J. Econ. Sci. Assoc.* 9(1): 123–135, doi:10.1007/s40881-023-00131-9. | fix |
| C4 | "Sangle et al., *Annals of Arid Zone*": the AAZ paper with that title is Meshram, Gorantiwar & Mittal 2010, 49(2), doi:10.56093/aaz.v49i2.63968. | source |
| C5 | ADR 0004: Dubois et al. 2020 compares mandatory disclosure with voluntary sharing (no group-total arm); Bigoni & Suetens 2012 is a public-goods game and points the other way for contribution feedback. The sentence overstates both. | fix |
| C6 | ADR 0004 "Ostrom 2009" is the SES framework paper, not an experimental-design source. | fix |
| C7 | Theis 1940, Konikow & Leake 2014, Bredehoeft et al. 1982, Yaari & Bar-Hillel, Young 1988, Constantine et al. are missing from §12.4. | fix |
| C8 | §11 unverified list is stale: Deutsch 1975, Konow 2003, Casal 2007, Young 1988 verified on Crossref. | fix |
| C9 | Unverified figures: Frohlich et al. "25 of 29 groups"; communication "a fifth to three-quarters" (Ostrom, Walker & Gardner); ~93 % covenant; Kenyan priority order beyond the reserve; Mwea seepage; Thiba 1.5-month buffer; PhilRice 42 person-days/ha; Cherry 2025 Eq. 3-13; progressive-farmer subsidies. | source |
| C10 | Hundepool et al. 2025 needs its full title (Handbook on SDC, 2nd ed.); van den Brink et al. 2010 has a 2012 JEEM version. | fix |

## D. What users read

| id | finding | status |
|---|---|---|
| D1 | Debrief "You voted for X" shows the table's chosen lens, not the player's vote; also in the review form. *Reproduced in code.* | fix |
| D2 | Private turn "The table will see how much was pumped, not by whom" overstates privacy (per-player debrief; measured inference during play). | fix |
| D3 | "Biggest harvest" maximises harvest value, not tonnes, once prices differ (Orchard). | fix |
| D4 | Floor-rule texts for CEA and capability describe the rules wrongly. | fix |
| D5 | Debrief row "Your water as used" is the whole table's. "Received" includes own pumping. "The table kept pumping private" when the facilitator alone chose. | fix |
| D6 | Join: "I agree to take part" with no information sheet; the pre-session checkbox attests to a survey that does not exist. | fix (remove the checkbox) + source (information sheet, ethics) |
| D7 | Review: "Only you see your answers" — answers are on the room server, which keeps rooms in memory only. | fix |
| D8 | README, CONTRIBUTING, GOVERNANCE, content/README, CITATION.cff and paper describe features that do not exist (apps/, store, builder, relay, role cards, PWA, Scenario Builder, a submitted JOSS paper, "no .zenodo.json"), name TypeScript as the engine, and leave the authoritative Python engine out of the science-review scope. | fix |
| D9 | paper.md: "cannot be computed from what is displayed beyond what the public total implies" contradicts ADR 0004's measured +6 to +11 points. | fix |
| D10 | Goal texts: "at least 75 %"; Authority goal is the table's total pumping averaged over seasons; the preview's "others do not pump" assumption is not shown. | fix |
| D11 | parameters.json role "FAO-33 survival threshold": the blueprint calls 0.5 a modelling convention at FAO's validity limit. | fix |

## Found while fixing

| id | finding | status |
|---|---|---|
| E12 | The join route (HTTP) did not broadcast `player.joined` to open sockets, so the facilitator's lobby never saw who had joined; it also mutated the game outside the room's lock, racing the WebSocket intents. | fix |

## Progress

- Batch 1 (engine), fixed with tests: E1 (verdict uses the applied floor rule; ties go to the voted lens; the chosen lens's debrief row uses the issued allocation), E2 (initial stock below the reserve refused; balance tests now require exact closure), E3 (unimplemented options refused at load), E4 (zero weights refused identically in both engines; κ > 0 in the schema), E5 (leximin tie-break in adequacy among optimal allocations, maintainer decision 2026-10-08; the TypeScript mirror refuses ties rather than return a different optimum), E6 (stable equally-distributed equivalent; finite-γ guard; overflow check at load), E7 (indicator values and Kᵧ ≤ 2 checked by the schema), E9 (collective score rounded), E10 (sealed `points` = full ΔL, shown on screen; audited), E12.
- E8 accepted: the residual is at most n × 1e-6 Mm³, within the §7.2 rounding rule; documented rather than re-rounded.
- Decisions recorded 2026-10-08: "whatever works" stays proportional (ADR 0003 unchanged); utilitarian ties by leximin adequacy (E5); B8 Drip and B23 S researched, proposals awaiting the maintainer.
