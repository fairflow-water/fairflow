<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Fairflow — Development Blueprint v3.1

Oct 5, 2026 · @Sg Yalew · IHE Delft · EquiNex Spatial Equity Modeling Suite

Version 3 is the build contract for the complete Fairflow. It consolidates the v2 blueprint (4 October 2026), the scientific audit and literature grounding, two expert reviews of v1 (game design, UI/UX) and four blind reviews of v2 (serious-game design, software architecture, water science, research methods), and one structural decision taken after those reviews: **the session is 120 minutes, not 90**, split into play and structured deliberation with measurement off the clock on both sides. Every number traces to a source in §12; every rule has a number; every screen has a layout and an acceptance test; every release has a gate that does not depend on a research result. Section 13 lists what changed from v2 and which reviewer finding drove it. Revision 3.1 (5 October 2026) adds the open-source structure: repository layout, the dual licence (MIT code, CC BY 4.0 content), SPDX and citation metadata at the first tag, and the publication plan (JOSS at v1.1, the serious-game paper with cohort data). Supersedes v2.

## 1. Vision, scope and releases

Fairflow is a phone-first progressive web app in which three to five water users and a basin authority share a river and an aquifer over five or six seasons, vote each season on which principle of distributive justice decides the split, act privately on what they receive, and are scored together on equity, efficiency and sustainability and separately on livelihood. It is the serious-game entry point of the EquiNex suite. Its purpose is to make one scientific proposition experienced rather than read: *there is no lens-free way to share scarce water — the allocation rule, the equity metric and the climate year each embed a theory of distributive justice, and the trade-offs between equity, efficiency and sustainability change with scarcity* (Yalew et al. 2024; Cherry 2025; Sharma et al. in prep.). The one UX idea the whole build serves: **the vote moves equity, the pumps move sustainability, and the reveal tells both as one short story.** The one facilitation idea: **play for an hour, then write the rule you wish you had had.**

### 1.1 Learning outcomes

1. Name the distributive-justice principles and state, for a given dry year, who gains and who loses under each.
2. Explain why two equity indicators computed on the same season can disagree, and which principle each silently assumes — including the game's own scoreboard.
3. Compare the rule chosen before allocation with the rule the outcome best satisfied after it (a priori versus a posteriori).
4. Describe the aquifer's trajectory, connect it to the incentive structure of private extraction, and design one institution that would change it (the deliberation task, §5.0).
5. Identify lock-in and the rebound effect when they occur, and the conditions under which cooperation held or failed.
6. Parameterise the basin from real-world data and say what the numbers assume. *A course outcome, assessed at the two-week review through the Scenario Builder, not inside the session.*

A seventh theme runs through the debrief rather than the scoring: *who decided, and whose claims counted* — procedural and recognition justice (Zwarteveen & Boelens 2014). The game is full of procedure (who holds the phone, the Authority's tie-break and veto, the River's seat, the negotiation clock) and the debrief asks about it once.

### 1.2 The complete game

| Part | Content |
| --- | --- |
| Basin | One river with a protected reserve, one shared aquifer with a reserve floor and natural recharge, return flows from non-consumed water, optional storage dam; three schemes by default, up to five; an optional ecosystem seat |
| Scenario Builder | Players or a facilitator enter real-world values for every parameter, guided by ranges and by worked examples with sources (fictional default, Balotra, Mwea, Omo–Gibe); a per-field sourcing guide; scenarios save, share and import as `scenario.json` |
| Lenses | Utilitarian (value-maximising), weighted utilitarian, strict egalitarian, proportional, capability, sufficientarian, prioritarian (γ), equal sacrifice, Talmud; user-defined criterion expressions in a closed grammar |
| Actions | Orchard, Drip, Expand, Pump; Steal and Monitor; Authority investments (monitoring, canal lining, storage dam, permit audit, rotation); binding side payments |
| Shocks | Climate deck per scenario (optionally non-stationary); event deck (pest, delayed rains, outgrowers, recharge, groundwater crisis, subsidy, price spike, basin plan) |
| Scoring | Three dials with two equity metrics and a switchable equalisandum, EES triangle, geometric-mean collective score, livelihood points, survival floor, ecosystem dial, a posteriori welfare scores, core-stability check, Shapley column |
| Session | 120 minutes: tutorial, five or six sealed seasons, reveal, Lederman debrief, institution-design deliberation; surveys before and after, not during |
| Play modes | Table mode (one shared phone, offline); room mode (phone each, room code, relay-sequenced); classroom mode (several tables, one facilitator screen); seat filling by server-side agents |
| Spatial | Schematic basin that recolours by public allocation adequacy; real geography from bundled GeoJSON with WaPOR-derived unit attributes via the authoring pipeline |
| Record | Append-only Season Record, replay, export, anonymised research dataset with event-level file; pre-, post- and delayed post-survey linked by a personal code; structured review form |
| Facilitation | Printed facilitator script with time-boxes, tutorial season 0, timers, Authority hand-over, time-box event, engine-generated debrief brief, treatment assignment |
| Agents | Scripted strategy agents for balance testing; Concordia generative agents for synthetic playtesting, seat filling and research |

### 1.3 Out of scope for the product

Live raster processing or WaPOR API calls on the device; shapefile upload in the app (the authoring pipeline converts offline); monthly reservoir operation computed live (Omo uses pre-computed policy cards); user accounts (rooms are codes, players are roles); any causal research claim from a single cohort.

### 1.4 Release train

| Release | Delivers | Gate |
| --- | --- | --- |
| v1.0 (build weeks 1–4; first student cohort) | Table mode; default basin; Builder limited to editing the default basin's numbers with a live allocation table; five classical lenses; Module 1 actions with the 2-pump cap and depletion-scaled cost; three dials, two-needle equity gauge, triangle stack, geometric-mean score; schematic map; Season Record with export and replay; tutorial season 0; three-beat reveal; two-line a posteriori verdict; time-box event and debrief brief; pre-survey by QR, delayed post-survey, review form; printed facilitator script with the 120-minute timetable | Definition of done (1.5); cohort-cut list (§8.3) decided at the week-3 pilot |
| v1.1 (weeks 5–9) | Room mode with a relay that runs the engine and sequences events; prioritarian, equal-sacrifice and Talmud lenses on by default; Modules 2–5 (position and theft, Authority budget, event deck, Voice of the River); full a posteriori welfare table; facilitator big-screen view; full Scenario Builder with import, share, sourcing guide and the Omo example; hash-proof display | Room mode passes the 120-minute timetable and the privacy test on two pilot tables; balance criteria met for every module; v1.0 cohort records exported cleanly; JOSS paper on the engine submitted |
| v1.2 (weeks 10–16) | Real-geography presets (Mwea, Balotra) from the WaPOR authoring pipeline; Omo–Gibe preset with policy cards; ET-scaled seasonal demand; Module 6 side payments; treatment assignment; localisation to Amharic and Hindi | Authoring pipeline reproduces the two papers' indicator values for their study years |
| v2.0 (weeks 17–26) | Agent layer: scripted agents in CI, Concordia seat filling and synthetic cohorts; research export schema frozen; EquiNex Policy Simulator consumes `@fairflow/engine` | Agents complete 100 unattended games without engine rejection; export schema frozen (any human–agent comparison is a research output, not a gate) |

### 1.5 Definition of done (every release, for the parts it delivers)

- Engine passes every reference vector in §3 to two decimals for every lens shipped, and every property test in §9.1.
- One full game plays on an Android and an iOS phone, exports, and replays identically on another phone of the other platform; table mode with the network off.
- No public screen, export or relay message shows per-scheme water received, adequacy, production or livelihood during play (the privacy test of §9.1).
- Scripted-agent balance model meets the pass criteria of §9.2 for every shipped scenario, with the sensitivity report attached.
- Two pilot tables complete play inside 80 minutes and the whole session (§5.0 timetable, including table deliberation) inside 120 minutes, with the facilitator acting only as Authority for seasons 0–2 and as debrief lead.
- Every number in a shipped `scenario.json` carries a `source` string resolving to §12; every user-entered value is stored with its unit, range check and provenance.
- The tag is REUSE-compliant (every file carries an SPDX identifier matching LICENSE or LICENSE-docs), CITATION.cff validates, and the release receives a Zenodo DOI (§7.5).

## 2. Scientific model

A discrete-season allocation and crop-response system for three to five irrigation schemes on one river over one shared aquifer. Deterministic given the climate draw and the players' decisions; every stored number is rounded to 1e-6 at the event boundary so that a record replays identically on JavaScriptCore and V8. Changes from v2 are marked **\[v3\]**.

### 2.1 State (per season t)

| Symbol | Meaning | Unit | Default initial |
| --- | --- | --- | --- |
| Iₜ | River inflow from the climate deck | Mm³ | Wet 22 / Normal 17 / Dry 12 |
| R | Ecological and domestic reserve | Mm³ | 2.0 |
| AWₜ | Allocable water, Iₜ − R | Mm³ | 20 / 15 / 10 |
| Dᵢ,ₜ | Gross seasonal irrigation demand at intake | Mm³ | 6.25 / 9.00 / 3.40 |
| Kᵢ,ₜ | Production capacity at full demand | t | 5,000 / 4,500 / 2,000 |
| Qᵢ,ₜ | River allocation | Mm³ | — |
| Pᵢ,ₜ | Private pumping | Mm³ | 0 |
| Wᵢ,ₜ | Water diverted, Q + P | Mm³ | — |
| Bₜ | Aquifer stock (the Bank) | Mm³ | 20.0; reserve B\_res = 5.0 |
| βᵢ | Consumptive fraction of diverted water; the rest returns to the system | — | drip 0.90 / flood 0.60 / sprinkler 0.75 |
| r₀ | Natural aquifer recharge per season | Mm³ | 1.0 |
| Lᵢ,ₜ | Cumulative livelihood points | points | 0 |

### 2.2 Parameters and grounding

| Parameter | Default | Grounding |
| --- | --- | --- |
| Demands Dᵢ | 6.25 / 9.00 / 3.40 | Area × gross seasonal depth: 625 ha drip orchard at 1,000 mm, 900 ha flooded paddy (1,000 households × 0.9 ha) at 1,000 mm, 340 ha sprinkler cereals at 1,000 mm; totals coincide with Yalew et al. (2024) Table 1. **\[v3\]** Demand is not climate-scaled in v1.0: a dry card cuts supply, not demand. ET-scaled seasonal depths (paddy \~1,200 mm, cereals \~800 mm, orchard \~1,000 mm, varying by card) arrive with WaPOR ETa in v1.2 and are a scenario option, because they change every fixture |
| Productivity per m³ diverted | 0.80 / 0.50 / 0.59 kg/m³ | Measured CWP per m³ ET: rice 0.6–1.6, wheat 0.6–1.7 (Zwart & Bastiaanssen 2004); conveyance and field losses place flooded paddy low, drip orchards high |
| Livelihoods Nᵢ | 81 / 2,000 / 42 | Rice \~42 person-days/ha/season (PhilRice); orchards 0.1–0.3 workers/ha. **\[v3\]** The units are mixed as inherited from the sources — A counts employees, B and C count households — so the capability lens and CWF weight A's workers against B's households. The v1.0 role cards say so in words; the Builder's sourcing guide (v1.1) forces one unit, "people whose livelihood depends on the water", and flags a mix |
| Yield response Kᵧ | 0.8 / 1.1 / 1.0 | FAO-66 Table 1 (citrus 0.8–1.1, wheat 1.0–1.15, maize 1.25); no FAO value for flooded rice or pomegranate — rice 1.1 after Bouman & Tuong (2001), flagged `assumed` |
| Inflow by card (stored as absolute values, never as factors of the normal year) | 22 / 17 / 12 | Interannual CV of runoff in semi-arid basins; dry-year demand/supply 1.9 matches Balotra draft 181–250 % of recharge |
| Reserve R | 2.0 (12 %) | Between Tennant's 10 % minimum and the Q95 reserve of Kenya's guidelines (Cherry 2025) |
| Consumptive fraction βᵢ | 0.90 drip / 0.60 flood / 0.75 sprinkler | Consumed and beneficial fractions in water accounting (Perry 2007; Perry, Steduto & Karajeh 2017); return flows recharge the aquifer and are reused, which is why cutting diversion rarely cuts consumption (Grafton et al. 2018) |
| Natural recharge r₀ | 1.0 Mm³/season | Monsoon recharge by the water-level-fluctuation method (Healy & Cook 2002; Sharma et al.); makes the use/recharge ratio teachable |
| Groundwater–surface coupling | Next season's inflow falls by (B\_low − Bₜ)/B\_low × 1 Mm³ while Bₜ < B\_low | Baseflow depends on aquifer head; river and aquifer are one system (Alley, Reilly & Franke 1999) |
| Aquifer B₀, B\_res, B\_low | 20 / 5 / 10 | \~1.2 years of inflow; B\_res stands for baseflow and environmental discharge (water-budget myth: Alley & Leake 2004) |
| Pump cap and cost | 2 Mm³; c = 2 + 6(1 − Bₜ/B₀) per Mm³, × seat multiplier 1.0 / 1.5 / 2.0 once Bₜ < B\_low; rationed pro rata when stock is short | Cost rises with depth to water (Balotra borewells 200–220 ft riparian vs 450 ft non-riparian) |
| Orchard | from t+1: D × 1.3, p × 2; cost 10 | Perennial lock-in; pomegranate bearing years 3–5 compressed |
| Drip | from t+1: D × 0.8 at constant K (WP × 1.25); cost 8 | Micro-irrigation cuts diversion, not consumption (Perry et al. 2017; Grafton et al. 2018) |
| Expand | from t+1: area, D and K × 1.2 (areaHa updated too, so E\_SE per hectare and the map polygon stay consistent); cost 5; repeatable | Rebound: efficiency gains spent on area (Ward & Pulido-Velazquez 2008; Mwea outgrowers) |
| Bands | Equity good > 0.90 / fair 0.75–0.90 / poor < 0.75; adequacy good > 0.80 / ok 0.68–0.80 / poor ≤ 0.68 (map colour only); efficiency good ≥ 0.95 / fair 0.85–0.95 / poor < 0.85; sustainability good ≤ 1.00 / warning 1.00–1.15 / unsustainable > 1.15 | Bastiaanssen et al. 1996; Karimi et al. 2019; Chukalla et al. 2022; Gleeson et al. 2012 |
| Game length and deck | T \~ Uniform{5, 6}, sealed; deck 1 W / 3 N / 2 D; **\[v3\]** optional non-stationary deck (`dryDrift`: the dry inflow falls by a fixed Mm³ per season) for climate-change scenarios, off by default | End-game effects (Janssen et al. 2011); every game meets scarcity. The RNG seed is a secret nonce committed by hash and revealed at the end; a seed derived from the game id, which is in the record, would seal nothing |

### 2.3 Allocation lenses

```latex
Q_i = \min\!\left(D_i,\; \frac{C_i}{\sum_{j \in U} C_j}\, AW^{(k)}\right),\quad \text{iterate over the uncapped set } U \text{ until no cap binds}
```

The engine's allocation module is a generic claims-problem solver (claims Dᵢ, estate AW, weights Cᵢ, optional floors, optional maximiser), so every rule below is configuration.

| Lens | Principle | Rule | Stated simplification |
| --- | --- | --- | --- |
| Utilitarian (value-maximising) | Aggregate welfare (Bentham 1789; Mill 1863; Harsanyi 1955); equimarginal benchmark (Harou et al. 2009) | Maximise Σ pᵢYᵢ: greedy by marginal value over the piecewise-linear production function | Kaldor–Hicks wealth, not utility; equal marginal utility of money assumed |
| Weighted utilitarian | Yalew et al. (2024) | Cᵢ = Kᵢ/Dᵢ | A contribution/desert rule (Deutsch 1975; Konow 2000), not a Harsanyi weighting; off by default |
| Strict egalitarian | Equal shares among claimants (Dworkin 1981) | Cᵢ = 1, capped = constrained equal awards (Aumann & Maschler 1985; Thomson 2003) | Equalisandum is the claimant |
| Proportional | Aristotle NE V.3; Konow 2001 | Cᵢ = Dᵢ, equal adequacy | Stated demand treated as legitimate need |
| Capability | Sen 1999; Nussbaum 2011 | Cᵢ = Nᵢ·κᵢ, κ default 1 (weighted CEA) | With κ = 1 it is equal water per head; κ from a vulnerability index makes it capability-based |
| Sufficientarian | Frankfurt 1987; Crisp 2003; Shields 2012 | Floor 0.5·Dᵢ for all (proportional scaling or CEA on floors if short), remainder by a configurable secondary rule (max value default; prioritarian or proportional) | Agronomic survival floor; no legal anchor comparable to the domestic human right to water (CESCR GC15) |
| Prioritarian (γ) | Parfit 1997; Atkinson 1970; Adler 2012 | Qᵢ ∝ wᵢ^(1/γ) Dᵢ^(1−1/γ); default w = 1, γ = 2 | Resource-, not well-being-prioritarian; γ → 1 equal shares, γ → ∞ proportional (maximin on adequacy, not Rawls's difference principle) |
| Equal sacrifice | Thomson 2003 | Constrained equal losses: Σ max(0, Dᵢ − λ) = AW | Punishes small claimants |
| Talmud | Aumann & Maschler 1985 | AW ≤ ½ΣD: CEA on half-claims; else Dᵢ/2 + CEL on half-claims | Equals equal sacrifice when no half-claim is exhausted |
| User-defined | — | Expression over D, K, N, κ, area, price and lens parameters in the closed grammar of §6.1, with optional floors | Builder reports which classical rule it reduces to |

Surplus above total demand recharges the aquifer: B ← B + (AW − ΣQ).

### 2.4 Production and livelihood

```latex
A_i = \frac{W_i}{D_i}, \qquad Y_i = \begin{cases} K_i\,\big(1 - K_{y,i}(1 - \min(A_i,1))\big) & A_i \ge 0.5 \\ Y_i(0.5)\cdot A_i/0.5 & A_i < 0.5 \end{cases}, \qquad \Delta L_i = \frac{p_i Y_i}{100} - c_p P_i - c_{\text{action}}
```

FAO-33 seasonal yield response (Doorenbos & Kassam 1979) with intake adequacy Wᵢ/Dᵢ standing in for ETₐ/ETₘ (demand and delivery are both gross, so β cancels), valid to a 50 % deficit; below the survival threshold the relation is replaced by a linear fall to zero — a modelling convention at FAO's own validity limit, not an agronomic finding. A ≤ 0.5 in two consecutive seasons is crop failure. Water above demand adds nothing to production.

### 2.5 Indicators

```latex
E_{PJ} = 1 - \frac{\sigma(A)}{\bar A}, \quad E_{SE}(u) = 1 - \frac{\sigma(W/u)}{\overline{W/u}},\ u \in \{1, \text{ha}_i, N_i\}, \quad F = \frac{\sum p_iY_i/\sum \beta_i W_i}{\sum p_iK_i/\sum \beta_i D_i}, \quad S = \frac{\sum \beta_i W_i}{\beta^{*} AW_t + r_0}
```

- E\_PJ: proportional-justice equity on adequacy (Cherry 2025 Eq. 3-13). E\_SE: strict-egalitarian equity on water per unit of the chosen equalisandum — per claimant (default, the lens card's rule), per hectare (Cherry's pixel CV) or per person (Pani Panchayat). Population SD; values can fall below 0 (CV > 1) and are clipped to \[−1, 1\] on the dial, to \[0, 1\] before any composite. Gini reported alongside with the n/(n − 1) correction.
- F: realised economic water productivity relative to design productivity at full demand (616.6 t/Mm³ in the default basin); F = 1 at full demand everywhere, > 1 when scarce water goes to high-value schemes, < 1 when water is pumped beyond need. **\[v3\]** The dial shows F per m³ *consumed* (the equation above); the debrief replay (S9) can flip it to F per m³ *diverted* (β dropped), because the two disagree exactly when Drip has been played — the Perry/Grafton point in one toggle.
- S: consumptive use over renewable supply, with β\* the demand-weighted mean consumptive fraction, so S = 1 when the whole river is diverted at the basin's own return-flow rate and pumping does not exceed natural recharge; S = 1 is the sustainability boundary in the sense of Gleeson et al. (2012). Pumping above r₀ pushes it over 1, and a Drip token raises consumption (β 0.6 → 0.9 on a 20 % smaller diversion) even as the river water it frees goes to others — the efficiency paradox made visible. In a wet year S < 1 by construction.
- Triangle vertices r₁ = max(E\_PJ, 0), r₂ = min(F, 1), r₃ = 1 − clip((S − 1.0)/0.6, 0, 1), so maximal pumping in a dry year (S ≈ 1.6) scores 0 and one cube each (S = 1.3) scores 0.5; area (√3/4)(r₁r₂ + r₂r₃ + r₃r₁) is the picture. **Collective score = mean over seasons of the geometric mean (r₁r₂r₃)^(1/3)**; crop failure is flagged beside it, never voids it. Daly's ordering (sustainability as a lexical cap) is the Builder's alternative display. The collective score is itself a lens: its equity vertex is proportional-justice equity, and the debrief says so ("the scoreboard chose fair shares of need; here is the same game scored per person"). There is no lens-neutral scoreboard; the game's honesty is to name the one it uses. The CV bands of Bastiaanssen et al. (1996) and Karimi et al. (2019) were defined for pixel-level within-scheme variation; applied to three schemes they are game conventions and the Builder labels them so.
- Ecosystem dial \[M5\]: reserve delivered / reserve required.

### 2.6 Aquifer

```latex
B_{t+1} = \max\!\big(B_{\text{res}},\; B_t + \max(0, AW_t - \textstyle\sum D_i) + r_0 + \textstyle\sum (1-\beta_i) W_i - \textstyle\sum P_i\big), \qquad I_{t+1} \mathrel{-}= \max\!\big(0, \tfrac{B_{\text{low}} - B_{t+1}}{B_{\text{low}}}\big)
```

Return flows (1 − βᵢ)Wᵢ recharge the aquifer, so flood irrigation feeds the bank that others pump (Mwea's outgrowers on drainage water); a depleted aquifer cuts next season's baseflow, so river and aquifer are one system and the water-budget myth is enacted rather than named. Pumping is impossible below B\_res; requests beyond available stock are rationed pro rata. Position enters through cost (seat multipliers once B < B\_low), never through the river allocation. With β = 1 and r₀ = 0 the model reduces to the v1 fixtures of §3; the β-fixtures are generated from the same code in build week 1 and both sets are kept.

### 2.7 A posteriori welfare functions

```latex
\mathrm{UWF} = \tfrac{1}{n}\sum s_i,\quad \mathrm{PWF}_\gamma = \sum \frac{s_i^{1-\gamma}}{1-\gamma},\quad \mathrm{SWF} = \begin{cases} 0 & \exists i: s_i < m_i \\ \tfrac{1}{2n}\big[\sum \min(1, s_i/m_i) + \sum \tfrac{s_i - m_i}{1-m_i}\big] & \text{else} \end{cases},\quad \mathrm{EWF} = 1 - G^*(s),\quad \mathrm{CWF} = \frac{\sum N_i s_i}{\sum N_i}
```

with sᵢ = min(Aᵢ, 1) floored at 0.01 and mᵢ = 0.5. PWF is the Atkinson (1970) isoelastic form, increasing in supply (the EMODPS-ogb3 repository applies it to the shortfall, which decreases in supply — a sign error to correct there). Scores are placed on \[0, 1\] through equally-distributed-equivalent supply ratios (PWF is reported as its EDE; the raw negative sums in the §3 columns are engine fixtures, not display values), never by dividing by a best value. Welfare functions are compared across lenses, column-wise, never against each other. The verdict names the lens whose ideal allocation for that season is nearest the realised allocation (smallest Σ|Aᵢ − Aᵢ\*|), so it maps one-to-one onto the lens cards; the welfare table is the debrief's second layer. The verdict shows "you voted X; the outcome best satisfied Y; the gap came from Z Mm³ of pumping".

### 2.8 Module equations

| Module | Rule | Grounding |
| --- | --- | --- |
| M2 Steal | Upstream i moves 1 Mm³ from i+1 before reveal; reversed and fined 6 if monitoring is active | Mwea gate removal; graduated sanctions (Ostrom 1990) |
| M2 Rotation (dry years) | Tail-end receives last; W\_tail −= 0.5 | Temporal inequity at Mwea tail units |
| M3 Authority budget | βₜ₊₁ = βₜ + 5 − spend; monitor 5/season, lining 15, dam 20, audit 3 | Water-fee economy; Thiba Dam |
| M3 Conveyance | Qᵢ × (1 − λ), λ = 0.20 unlined; seepage λQᵢ recharges the aquifer; lining sets λ = 0 and removes that recharge | 40–50 % seepage at Mwea, 20 % so the lens still dominates. **\[v3\]** The lining paradox: lining delivers more to the field and less to the bank — correct hydrology (Perry et al. 2017) and a debrief moment; the Authority's investment card states it, and the balance sweep checks that lining is still sometimes worth buying |
| M3 Dam | Hold ≤ 3 Mm³ of surplus; AW += held in the next dry season | 1.5-month Thiba buffer |
| M3 Audit | Unlocks the Authority veto | Untraceable NIA permit |
| M4 Events | Pest Y × 0.86; delayed rains A\_tail × 0.85; outgrowers B − 1.5 or a 4th claimant D = 1.5; riparian recharge cₚ = 1 upstream; groundwater crisis B − 3; subsidy Orchard cost 0 once; price spike p × 1.5 orchards; basin plan re-vote | Makale et al. 2024; Cherry 2025; Sharma et al. |
| M5 River | Fifth voter; may raise R to 3 once; breach ⇒ Y × 0.9 all next season | Te Awa Tupua Act 2017; Kenyan priority order |
| M6 Side payments | Binding offer (i → j, amount, lens), paid at reveal if that lens won | Coasean compensation |
| Core stability (a posteriori) | v(C) = production of coalition C sharing Σ\_{i∈C} Qᵢ optimally; in core if no coalition's realised production < v(C) | Ambec & Sprumont 2002; Madani et al. 2014 BASI (degenerates to CV of shares when minimal rights are zero) |
| Shapley column | φᵢ over v(C) | Dinar & Hogarth 2015 |

## 3. Reference vectors and fixtures

Computed from §2 for the default basin, no actions, no pumping, **with β = 1 and r₀ = 0** (the v1 reduction of §2.6); the engine's unit-test fixtures (`fixtures/default-basin-v1.json`, two decimals). E\_SE per claimant. Wet year (AW = 20): every lens gives Q = 6.25 / 9.00 / 3.40, 1.35 Mm³ to the aquifer, A = 1, ΣY = 11,500 t, E\_PJ = 1.00, E\_SE = 0.63, F = 1.00, S = 0.93.

**\[v3\]** A second fixture set, `fixtures/default-basin-beta.json`, is generated from the same engine code on build day 3 with β = 0.90 / 0.60 / 0.75 and r₀ = 1. Allocations Q and adequacies A are identical in both sets (β cancels in §2.4); production, E\_PJ and E\_SE are identical; only F, S, r₃ and the aquifer trajectory differ. Both sets are kept and both are checked in CI; the β set is the one the shipped scenario uses. The tables below are therefore the allocation truth for every version and the scoring truth for the v1 reduction only.

### 3.1 Dry year, AW = 10

| Lens | Q A / B / C | A A / B / C | Y A / B / C (t) | ΣY | E\_PJ | E\_SE | F | UWF / PWF₃ / EWF / CWF / SWF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Utilitarian | 6.25 / 0.35 / 3.40 | 1.00 / 0.04 / 1.00 | 5,000 / 157 / 2,000 | 7,158 | 0.33 | 0.28 | 1.16 | 0.68 / −331.6 / 0.69 / 0.09 / 0 |
| Weighted utilitarian | 4.24 / 2.65 / 3.12 | 0.68 / 0.29 / 0.92 | 3,712 / 1,192 / 1,833 | 6,736 | 0.59 | 0.80 | 1.09 | 0.63 / −7.46 / 0.78 / 0.32 / 0 |
| Strict egalitarian | 3.33 / 3.33 / 3.33 | 0.53 / 0.37 / 0.98 | 3,133 / 1,500 / 1,961 | 6,594 | 0.59 | 1.00 | 1.07 | 0.63 / −5.92 / 0.78 / 0.39 / 0 |
| Proportional | 3.35 / 4.83 / 1.82 | 0.54 / 0.54 / 0.54 | 3,145 / 2,204 / 1,072 | 6,421 | 1.00 | 0.63 | 1.04 | 0.54 / −5.22 / 1.00 / 0.54 / 0.54 |
| Capability (κ = 1) | 0.66 / 9.00 / 0.34 | 0.11 / 1.00 / 0.10 | 632 / 4,500 / 201 | 5,333 | −0.05 | −0.20 | 0.86 | 0.40 / −95.1 / 0.50 / 0.95 / 0 |
| Sufficientarian | 3.80 / 4.50 / 1.70 | 0.61 / 0.50 / 0.50 | 3,432 / 2,025 / 1,000 | 6,457 | 0.91 | 0.64 | 1.05 | 0.54 / −5.35 / 0.96 / 0.50 / 0.54 |
| Prioritarian (γ = 3 fixture) | 3.40 / 4.34 / 2.27 | 0.54 / 0.48 / 0.67 | 3,176 / 1,951 / 1,333 | 6,459 | 0.86 | 0.75 | 1.05 | 0.56 / −4.97 / 0.93 / 0.49 / 0 |
| Equal sacrifice | 3.37 / 6.12 / 0.52 | 0.54 / 0.68 / 0.15 | 3,155 / 2,914 / 304 | 6,373 | 0.51 | 0.31 | 1.03 | 0.46 / −24.5 / 0.74 / 0.66 / 0 |
| Talmud | 3.12 / 5.18 / 1.70 | 0.50 / 0.58 / 0.50 | 3,000 / 2,396 / 1,000 | 6,396 | 0.93 | 0.57 | 1.04 | 0.53 / −5.51 / 0.97 / 0.57 / 0.53 |

### 3.2 Normal year, AW = 15

| Lens | Q A / B / C | A A / B / C | Y A / B / C (t) | ΣY | E\_PJ | E\_SE | F |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Utilitarian (= weighted = sufficientarian here) | 6.25 / 5.35 / 3.40 | 1.00 / 0.59 / 1.00 | 5,000 / 2,492 / 2,000 | 9,492 | 0.78 | 0.76 | 1.03 |
| Strict egalitarian | 5.80 / 5.80 / 3.40 | 0.93 / 0.64 / 1.00 | 4,712 / 2,740 / 2,000 | 9,452 | 0.82 | 0.77 | 1.02 |
| Proportional | 5.03 / 7.24 / 2.73 | 0.80 / 0.80 / 0.80 | 4,217 / 3,531 / 1,609 | 9,357 | 1.00 | 0.63 | 1.01 |
| Capability (κ = 1) | 3.95 / 9.00 / 2.05 | 0.63 / 1.00 / 0.60 | 3,529 / 4,500 / 1,205 | 9,234 | 0.76 | 0.41 | 1.00 |
| Prioritarian (γ = 3 fixture) | 5.10 / 6.50 / 3.40 | 0.82 / 0.72 / 1.00 | 4,264 / 3,126 / 1,999 | 9,389 | 0.86 | 0.75 | 1.02 |
| Equal sacrifice (= Talmud here) | 5.03 / 7.78 / 2.18 | 0.81 / 0.86 / 0.64 | 4,221 / 3,831 / 1,284 | 9,336 | 0.88 | 0.54 | 1.01 |

S = 1.00 and r₃ = 1 in every row of both tables under the v1 reduction. Three normal-year coincidences are fixtures: utilitarian equals weighted utilitarian (the maximiser fills the productive schemes first), sufficientarian equals utilitarian (every floor is met before the remainder — the shift thesis), equal sacrifice equals Talmud (no half-claim exhausted).

### 3.3 Dynamic fixtures

| Fixture | Setup | Expected |
| --- | --- | --- |
| Pumping | Normal, proportional, each pumps 2 | W = 7.03 / 9.24 / 4.73; A ≥ 1 all; ΣY = 11,500; F = 0.89; S = 1.40, r₃ = 0.33; B = 14; cost 2 × 2 = 4 each |
| Depletion | Dry, Dry, Normal, each pumps 2; B\_res = 5 | B = 14, 8, 5; season 3 rations 6 requests to 3 (1 each); cost per cube 3.8, 5.6, 6.5 before seat multipliers |
| Natural recharge | r₀ = 1 | Bₜ₊₁ = Bₜ + surplus + 1 − ΣP |
| Return flow (β set) | Normal, proportional, no pumping | aquifer gains Σ(1 − βᵢ)Wᵢ = 0.50 + 2.90 + 0.68 = 4.08 Mm³ plus r₀ |
| GW–SW coupling | B falls to 8 | next inflow reduced by 0.2 Mm³ |
| Orchard lag | A plays Orchard in season 2 | D\_A = 8.125, p\_A = 2 from season 3; L\_A −= 10 in season 2 |
| Drip then Expand | A: Drip season 1, Expand season 2 | D\_A = 5.0, K\_A = 5,000 from season 2; D\_A = 6.0, K\_A = 6,000, area 750 ha from season 3; ΣD 17.4 then 18.4 with 20 % more capacity — the rebound |
| Crop failure | C at A ≤ 0.5 in seasons 2 and 3 | flag set; score still computed |
| Game length | 100 nonces | T ∈ {5, 6}, each 0.50 ± 0.05; deck 1 W / 3 N / 2 D always yields a dry season; commitment verifies for every nonce |
| Goal attainability | Full cooperation, proportional, 1W/3N/2D | A reaches 79.8 % of potential, so the 75 % goal (R15) is met without pumping and the old 80 % was not |
| Equalisandum | Dry, proportional; switch u | E\_SE per claimant 0.63; per hectare 1.00 (= E\_PJ); per person 0.35 |
| Verdict match | Dry, proportional voted | EWF highest; verdict matches vote; pumping gap 0 |
| Verdict mismatch | Dry, utilitarian voted | UWF 0.68 is the highest UWF of any lens in this season (column-wise comparison); PWF₃ −331.6, SWF 0; every other principle ranks it worst |
| Prioritarian limits | γ = 1.001 and 1,000 | within 0.01 of strict egalitarian and proportional |
| Time-box | `game.timeboxed` after season 3 of a T = 5 game | game ends after season 3; T and deck still unseal; hash verifies; `truncated: true` |
| Timer expiry | S4 closes with no proposal in season 3 | previous season's lens applied; `lens.chosen` carries `byTimeout: true` |
| Replay determinism | any record | replay on JavaScriptCore and V8 yields byte-identical `seasons.csv` |
| Privacy | Normal, any lens, A pumps 2 | no public projection, export before debrief or relay message contains W\_A, A\_A, Y\_A, ΔL\_A or P\_A; total pumping = 2 |

### 3.4 Cross-checks

- Strict egalitarian normal-year row reproduces Figure 1 of Yalew et al. (2024); `weighted_utilitarian` reproduces its direction (B at 5.35 vs the paper's 5.70, which also weights total production; a `yalew2024` flag reproduces it exactly).
- Dry year: strict egalitarian scores E\_SE = 1.00, proportional E\_PJ = 1.00 by construction — each metric awards a perfect score to the lens that embodies it (metric-is-a-lens).
- Capability with κ = 1 drives E\_PJ below zero while per-person E\_SE is highest (0.75): the equalisandum point.
- Strict utilitarian dry year (cooperative at 4 %, PWF −331.6) is Rawls's separateness-of-persons objection in numbers.
- Marginal production per Mm³ of deficit water is K·Kᵧ/D: 640 / 550 / 588 t, i.e. 6.4 / 5.5 / 5.9 points at p = 1, against a pump cost of 2.0 at B₀, 3.8 at 14, 5.6 at 8 and 6.5 at 5. Every scheme profits from every cube until B < B\_low; then seat multipliers price out B (8.4) and C (11.2) while A (5.6 < 6.4) keeps pumping to the floor — the Balotra riparian story emerging from the parameters. This is the intended shape of the dilemma (§9.2).

## 4. Rules specification

&#91;Mₙ\] marks a rule active only with module n enabled. Rules changed since v2 are marked **\[v3\]**.

### 4.1 Setup

- **R1.** A game is created from a scenario and a play mode; the scenario fixes every parameter of §2 and the module flags. **\[v3\]** The treatment arm (silent mode, universalisation nudge, Authority hand-over season) is written as a `treatment.assigned` event before season 1, with who assigned it.
- **R2.** Roles: one player per scheme (3–5), one Basin Authority, \[M5\] one Voice of the River. Table mode: roles in seat order on one phone, the Authority holds the phone in every public phase. Room mode: join by code, pick a free role.
- **R3.** **\[v3\]** Consent, pre-survey and the personal linking code are completed before the session on the player's own phone (QR sent the day before; paper on arrival for anyone who has not). Nobody sees a role card before the pre-survey closes. Season 0 is a facilitated tutorial budgeted at 10 minutes: normal year, two lenses (proportional, utilitarian), one practice private turn with pump cost 0, nothing scored; it is an engine mode, not a separate screen set. The facilitator plays the Authority for seasons 0–2 and hands over; the hand-over is an event.
- **R4.** T \~ Uniform{5, 6}, sealed by hash of a secret nonce at creation, revealed after season T or at a time-box. Deck 1 W / 3 N / 2 D, shuffled at creation, order sealed the same way.
- **R5.** B₀, B\_res, \[M3\] budget 0, livelihood 0.

### 4.2 Season sequence

- **R6. Climate.** The app reveals the card; R to the River; AW shown. \[M4\] One event card revealed and queued.
- **R7. Proposal.** Lenses are proposed aloud; the Authority taps them. The negotiation timer (R20) starts when the lens screen opens. Arguments are spoken; the record keeps lens and proposer. \[M6\] Side-payment offers in this window.
- **R8. Vote.** Each scheme player states a vote and the Authority taps the chip (the phone does not travel for a public vote); \[M5\] the River votes. Plurality wins; the Authority breaks ties and holds one veto per game \[M3: after a permit audit\], after which the remaining lenses are re-voted. Timer expiry with no proposal applies the previous season's lens (the scenario's default lens in season 1); `lens.chosen` records `byTimeout`.
- **R9. Allocation.** Engine computes Qᵢ under the lens, \[M3\] conveyance loss, \[M2\] rotation in dry years; the winning row expands into the map and cubes flow; surplus to the aquifer.
- **R10. Private decisions.** In seat order each scheme player receives the phone via the hand-over screen, sees their own previous-season results, plays at most one Action token and 0–2 Pump tokens, \[M2\] may Steal if upstream of another scheme, and commits; 0:45 from the receiver's tap. Waiting players answer the hand-over prediction prompt aloud and the Authority taps the answer. The Authority is skipped unless \[M3\]. \[M3\] the Authority invests within budget.
- **R11. Reveal.** Pumps draw from B down to B\_res, rationed pro rata when short; \[M2\] Steal applied or reversed and fined under monitoring; W, Y, ΔL computed; \[M4\] event effects applied; return flows and natural recharge credited to B; dials, gauge and triangle updated; total pumping shown; two-sentence read-back; `season.resolved` closes the season.
- **R12. Carry-over.** Orchard, Drip and Expand take force from t+1; pump cost recomputed from B with seat multipliers; next season's inflow reduced if B < B\_low; \[M3\] dam storage carried; \[M5\] reserve breach queues the penalty.

### 4.3 Actions and costs (default basin)

| Action | Who | Limit | Cost | Effect |
| --- | --- | --- | --- | --- |
| Orchard | Scheme | once | 10 | t+1: D × 1.3, p × 2 |
| Drip | Scheme | once | 8 | t+1: D × 0.8 at constant K; β → 0.90 |
| Expand | Scheme | repeatable | 5 | t+1: area, D, K × 1.2 |
| Pump | Scheme | 0–2 / season | 2 + 6(1 − B/B₀) per Mm³ × seat multiplier when B < B\_low | W += P; B −= P, ≥ B\_res |
| Steal \[M2\] | upstream scheme | 1 / season | 0; fine 6 if detected | 1 Mm³ from next downstream |
| Monitor \[M3\] | Authority | per season | 5 | detects Steal; reveals pumps |
| Line canals \[M3\] | Authority | once | 15 | λ = 0; seepage recharge ends (card says so) |
| Dam \[M3\] | Authority | once | 20 | hold ≤ 3 Mm³ for the next dry season |
| Audit \[M3\] | Authority | once | 3 | unlocks veto |
| Raise reserve \[M5\] | River | once | — | R = 3 if the vote passes |
| Side payment \[M6\] | Scheme | per season | offered amount | paid if the named lens wins |

### 4.4 Scoring and goals

- **R13.** Per season: A, Y, ΔL, L, E\_PJ, E\_SE (all equalisanda), G\*, F (consumed and diverted), S, B, \[M5\] ecosystem dial, welfare scores, verdict, core check.
- **R14.** Collective score = mean geometric mean (§2.5); crop failure flagged, not voiding. The debrief names the score's own lens.
- **R15.** Private goals, each attainable without pumping: A — cumulative livelihood ≥ 75 % of its full-demand potential (**\[v3\]** was 80 %, which the fully cooperative proportional path misses at 79.8 %); B — adequacy never < 0.5; C — adequacy ≥ 0.8 in at least half the seasons; Authority — average pumping ≤ 2 Mm³/season and reserve never breached; \[M5\] River — ecosystem dial never < 1. Livelihood is judged within a scheme, never across.
- **R16.** No single winner: collective score, goals met or missed, and the per-season verdict are shown.

### 4.5 Information

- **R17.** Public: climate, AW, Qᵢ, dials, gauge, triangle, aquifer stock, total pumping, votes and proposals. Not public during play: Wᵢ, Aᵢ, Yᵢ, ΔLᵢ, Pᵢ (W − Q reveals pumping); each player sees their own privately at the start of their next turn; the map colours by Qᵢ/Dᵢ until the debrief. **\[v3\]** "Public" means every surface: screens, the shared display, any export made before the debrief, and every message a relay sees in clear.
- **R18.** Private until the debrief: who pumped how much, Steal, untriggered offers. \[M3\] Monitoring makes the season's pumps public.
- **R19.** The debrief reveals everything **after the facilitator has spoken the safety norm** (§5.3); a table may opt to keep per-player pumping sealed and discuss totals only, recorded as `debrief.opened {perPlayer: false}`. Exports carry roles, never names.

### 4.6 Timing

- **R20. Timing (120-minute session).** **\[v3\]** Negotiation 3:00 from screen open in seasons 0–2 and 4:00 from season 3 (arguments get harder once the aquifer is visibly falling); private turn 0:45 from the receiver's tap, auto-commit with a 3 s undo toast. Budget: season 0 in 10 minutes, seasons 1–T in 10–11 minutes each with three schemes, so play runs 60–75 minutes for T ∈ {5, 6}. A facilitator **time-box event** (`game.timeboxed`) at minute 80 of the session ends play after the current season without breaking the hash reveal; the record marks the game as truncated. Consent, pre-survey and linking code happen before the session; the review form, the six written prompts and the delayed post-test after it. The session timetable is §5.0.

## 5. Experience specification

### 5.0 How a session runs

**The 120-minute session.** Fairflow is played in one two-hour slot: an hour of play, then structured reflection, with measurement before and after rather than inside. The 90-minute box of earlier versions did not close once the beats were timed (season 0 alone needs 8–10 minutes; six seasons at 10 plus a 20-minute debrief reaches 85 before role cards, hand-overs and surveys), and the deliberation block is where learning outcome 4's "institutions that change it" is actually taught in a cohort that has no Module 3.

| Minute | Block | What happens | Who leads |
| --- | --- | --- | --- |
| before | Consent, pre-survey, linking code | QR link sent the day before; closes when the session opens; students who have not answered do it on paper on arrival | self |
| 0–05 | Arrival and table formation | Phones out, roles drawn, shared phone identified (table mode) or room code joined (room mode) | facilitator |
| 05–15 | Season 0 (tutorial) | Two lenses only, unscored, pump cost 0; role cards read aloud; one full loop through negotiate → vote → private turn → reveal | facilitator as Authority |
| 15–80 | Seasons 1–T | Sealed T ∈ {5, 6}; Authority hand-over after season 2; negotiation 3:00 then 4:00 from season 3; time-box event at minute 80 if still playing | table |
| 80–85 | Reveal and decompress | Deck order and length unsealed, hash shown, scoreboard; facilitator reads the engine's three-line debrief brief; safety norm spoken before `pumpsBy` is unsealed | facilitator |
| 85–105 | Hot debrief (Lederman) | Describe (5): what happened, from the predictions recorded at hand-over. Analyse (10): replay over S9, flip the equalisandum once, flip F consumed/diverted if Drip was played, dry-season case, voted lens vs satisfied lens, one question on who decided and whose claims counted. Generalise (5): Balotra and Mwea | facilitator |
| 105–120 | Table deliberation | Institution-design task on one sheet per table: “Write the one rule you would add before season 1, who enforces it, and what it costs.” Each table reads its rule aloud (one minute each); the facilitator keys the rules into `debrief.note` | tables |
| after | Review form (S10), six written prompts, delayed post-test | Homework; delayed post-test and cold debrief with the record at the two-week review | self, then class |

The split is roughly 65 minutes of play, 25 of debrief, 15 of deliberation and 15 of logistics. If a cohort can only be given 90 minutes, the table deliberation moves to the two-week review and the time-box fires at minute 60; nothing else changes. The deliberation sheet is per table, not per person: one rule by consensus forces the pumper and the pumped-upon to agree, which is the Ostrom lesson; a per-person variant is a scenario flag for research use.

**Who sees what.** Fairflow is a table game with a digital referee, not a quiz. Everyone sits together and talks; the app holds the rules, the numbers and the record. Three configurations share one engine and one record and differ only in which screens are on which device.

| Configuration | Devices | Public state (climate, map, vote, reveal, debrief) | Private turn (pump and action tokens) | Network | Release |
| --- | --- | --- | --- | --- | --- |
| **Table mode** | One phone per table, held by the Authority (the facilitator for seasons 0–2, then a student) | On the one phone, read aloud and turned toward the table; an optional second device mirrors it as a big screen by import | The phone is passed; a hand-over screen separates players | None | v1.0 |
| **Room mode** (Mentimeter-like) | One phone per player plus a shared screen (projector or a laptop) | On the shared screen, driven by the relay; each phone shows only its own role's view | On each player's own phone, simultaneously, within one timer | Required (room code) | v1.1 |
| **Classroom mode** | Several tables, each in table or room mode; one facilitator screen | Per table as above; the facilitator screen shows every table's dials and aquifer side by side for the plenary debrief | As per table | Required for the aggregate view | v1.1 |

**Table mode, as played.** Four students sit around one phone. The Authority opens the season: the climate card flips, the table reads the sentence aloud, the river widens or narrows on the map. The Authority taps proposals as players argue; when the clock runs out players say their votes and the Authority taps the chips; the winning row floods the map. Then the phone travels: a hand-over screen with the next player's shape and a prediction question for the others; the player decides in 45 seconds and hands on. When the last has committed, the Authority turns the phone back to the table for the three-beat reveal. The debrief runs from a printed script with the replay on the phone. Nothing needs Wi-Fi.

**Room mode, as played.** Each student opens the room code on their own phone and takes a role; the shared screen shows the basin. The vote happens on each phone with the tally on the big screen (live, or only at Close the vote in the secret-ballot treatment); the private turn happens on all phones at once (no passing, no idle time); the reveal plays on the big screen while each phone shows that player's own results. This is the familiar Mentimeter shape — audience devices as controllers, one shared display as the stage — and it removes the two weaknesses of table mode (hand-over idle time and pass-the-phone privacy). It costs a relay, a room code flow, and dependence on the venue's network, which is why it is v1.1: table mode first, because it cannot fail in a classroom. If the venue network dies, the host exports the record and the table continues in table mode from the last event.

**Facilitator versus participants.** In every configuration the facilitator sees the same public state as the players plus three things: the printed script, the engine's three-line debrief brief at the reveal (heaviest pumping season, lens switches, verdict mismatches — computed from the record the moment play ends, so the facilitator is not preparing a debrief blind), and from v1.1 the facilitator screen with per-table dials and the hand-over latency log. The facilitator never sees private actions before the debrief either; the game's credibility depends on that, and the record proves it.

### 5.1 Design principles

- Design viewport 360 × 640 CSS px, portrait. A 56 px persistent header (season, climate glyph, the aquifer as a tank whose height is Bₜ with B\_res hatched, the lens in force) and a 64 px bottom action bar in the thumb zone on every screen.
- One idea per screen. At most 15 numbers on any screen, 8 on a private turn, 5 on a reveal page, 3 on the map. Nothing scrolls on S3–S7.
- The Authority holds the phone in every public phase; only the private turn travels.
- Show who gets what, not what the principle means: the engine turns every lens into this season's numbers, and the UI shows those as share-bars with a plain-language name and a generated "who gets more" line; the academic name is a 12 px subtitle; the card back is one tap away.
- Motion carries meaning or is absent: river width eases to inflow; polygons fill to allocation; the tank drops a notch per pumped cube on the stepper and drains by the total at the reveal; needles swing; the triangle drops onto its ghosts. Every motion has a reduced-motion end state and every haptic has a visual twin.
- Bands are read from needle position on a fixed three-segment arc with the band word (good / ok / poor); colour is decorative. Schemes are identified by shape, crop glyph and river position (circle–pomegranate upstream, square–rice midstream, triangle–wheat tail), consistent across map, bars, banner and hand-over.
- Copy: second person, present tense, concrete nouns, units always; no "-arian" on a front face; never "win", "lose", "cheat" or "secret". Word budgets: map ≤ 25, lens screen ≤ 60 beyond the rows, hand-over ≤ 20, private turn ≤ 70 with tokens collapsed, read-back two sentences and ≤ 40 words with ≤ 4 numbers, role card ≤ 120 words, lens back ≤ 60.

### 5.2 Screens

| # | Screen | Layout and interaction (zones in px from the top) | Acceptance |
| --- | --- | --- | --- |
| S0 | Home | New game (scenario → mode); Scenario Builder; Load record; Examples; About and sources | Offline after first load; every example opens with every parameter and its source |
| S1 | Scenario Builder | v1.0: basin and scheme fields of the default basin, each with unit, range, example chips (Default, Balotra, Mwea) that fill the value and show its source; derived values and the Allocation table update live; hard checks block (scarcity, reserve < dry inflow), soft checks warn and flag `out_of_range`; save. v1.1: lens, action and module steps, per-field sourcing guide (one people-unit, depth per crop, where to find β), import, share, Omo example | Re-entering the default basin reproduces §3 exactly; a no-scarcity basin is refused with the reason; a lens `criterion` outside the §6.1 grammar is refused at load with a named error |
| S2 | Pre-session and join | On the player's own phone, the day before: consent, pre-survey, personal linking code (`linking.code`). On the shared phone at the table: role assignment only, by linking code; Authority hand-over option | `player.joined` carries consent, pre-survey and code before any role is shown; no form on the shared phone is longer than one screen |
| S3 | Climate and map | 56–200 climate card flip and its sentence ("Dry year. 12 Mm³ arrived, 2 stay in the river, 10 to share"); 200–520 schematic basin: river width ∝ inflow, reserve reach marked, polygons sized by demand and coloured by last season's public Q/D (outlines in season 1), tank in header; 520–576 one line on last season; CTA "Decide how to share it"; \[M4\] event card behind a tap | Colours equal public Q/D band words; river width within 2 px of ∝ inflow; 3 numbers |
| S4 | Lens vote | 56–96 shrinking negotiation bar (seconds only in the last 30) and lens in force; 96–436 five rows at 68 px: plain name + glyph, three share-bars filled to this season's adequacy with the percentage, "who gets more" line, academic name 12 px; tap a row for its back as a bottom sheet; 436–576 vote chips (tap row, Authority taps the scheme's chip as the player speaks; tally visible); Authority tie-break and veto in a modal; CTA "Close the vote". The winning row expands into the map and polygons fill over 1 s (this replaces a separate allocation screen). Season 0 shows two rows | Share-bar lengths equal Aᵢ to 1 %; chips ≥ 48 px; timer starts on screen open at the R20 length for the season; expiry with no proposal applies the previous lens (default in season 1), as R8; 15 numbers max |
| S6 | Private turn | Hand-over screen first: full-bleed in the receiver's shape and name, the table's spoken prediction prompt in 20 px type with the Authority's tap to record the answer, one button "I am the Cooperative" that starts the 45 s ring. Then 56–120 role banner with own previous results ("you received 3.4 of your 6.3; harvest 1,600 t; +16 points"); 120–160 timer ring; 160–278 pump card first: 0–2 stepper framed as borrowing, cost line, tank dropping a notch per cube, net-gain line recounting (+620 t → +6 pts − 2 pts), "the table will see how much was pumped, not by whom"; 278–470 three action tokens collapsed to one line with cost, expanding in place; 470–560 running livelihood; CTA hold-to-commit with 3 s undo. Authority skipped in v1.0; \[M2\] Steal; \[M6\] offer | Nothing of the previous player visible; timer starts on the receiver's tap; auto-commit toast; a pump beyond stock shows the rationing; stepper and role button ≥ 48 px; 8 numbers max |
| S7 | Reveal | Three paged beats, tap to advance. Beat 1: tank drains by total pumping with a per-cube tick and a rising counter ("The table pumped 4 Mm³"); the sustainability needle alone; low tone if it crosses 1.0. Beat 2: the two-needle equity gauge — one arc, three fixed segments, needles fair shares of need (E\_PJ) and equal amounts (E\_SE) — under a one-sentence read-back. Beat 3: the triangle drops onto the ghosted stack, axes Fair · Productive · Lasting with formal names as subtitles; F small beside it. CTA "Next season"; "Per scheme" sheet with public Qᵢ and total pumping only | Needles and vertices equal `season.resolved` to 1 %; read-back numbers equal `season.resolved`; no per-scheme W, A, Y, ΔL, P visible; band readable with colour removed; 5 numbers per page |
| S8 | Game end | T revealed (hash proof recorded, displayed from v1.1); `truncated` badge if time-boxed; collective score with crop-failure flag; goals met or missed; the three-line debrief brief for the facilitator; Go to debrief (which spells out the safety norm and asks "reveal who pumped?" yes/no, recorded) | Revealed length and deck hash to the commitments (engine test); the brief is computed from the record only |
| S9 | Debrief | 56–120 season tabs; 120–380 triangle stack and two-needle gauge; 380–480 two-line verdict; 480–560 equalisandum segmented control re-swinging the E\_SE needle and an F consumed/diverted toggle; per-scheme pumping unlocked in the sheet if the table agreed; the recorded predictions beside each season; export. Facilitator script on paper | Selecting season k shows the state after `season.resolved` k; the equalisandum moves only the E\_SE needle; the F toggle moves only F; 7 numbers max |
| S10 | Review | Parts 1–3 of the review form; progress saved locally; `review.answer` events | Offline, resumable |
| S11 | Facilitator view (v1.1) | Mirrors S3, S4 and S7 for a room; no private data; time-box button | Read-only via sync except the time-box |
| S12 | Load and replay | Import, validate, replay with season tabs, compare two records | A record exported on one phone replays identically on another phone of the other platform |

### 5.3 Content

- **Role cards** (≤ 120 words): name, seat, demand, productivity, people (with the unit stated: employees or households), three sentences of situation from the source interviews, the private goal (R15), two things the player knows that others may not.
- **Lens cards.** Front: plain name and glyph, this season's share-bars and "who gets more" line, academic subtitle — *Biggest harvest* (grain sack on a tipped scale), *Same for each* (three identical cubes), *Same share of need* (three different cubes filled to one line), *Per person* (a row of figures), *Enough first* (a floor line with bars above). Back (≤ 60 words): principle, rule, what it leaves out, a real case with source (progressive-farmer subsidies; Pani Panchayat; Mwea rotation; Andhra Pradesh borewell pooling; Anantapur protective irrigation; Madani et al. 2014 and Aumann & Maschler 1985 for the v1.1 cards).
- **Read-back templates**: two sentences per season generated from `season.resolved`, at most four numbers.
- **Debrief** (25 minutes plus 15 of table deliberation, printed facilitator script, Lederman's phases; timetable in §5.0): reveal and decompress with the safety norm spoken before pumpsBy is unsealed — "the rules made pumping rational; we debrief the rules, not the person" (5); describe from the recorded hand-over predictions (5); analyse over the replay with spoken prompts 2, 5 and the dry-season case of 6, flipping the equalisandum once, flipping F once if Drip was played, and one question on who decided and whose claims counted (10); generalise to Balotra and Mwea (5); then the institution-design deliberation, one rule per table, read aloud and keyed into `debrief.note` (15). Branches for: no dry season, one dominant voter, pumping from season 1, facilitator played the Authority, game time-boxed. Each phase carries its time-box on the script. The six written prompts (equity rose by narrowing or by more water; which metric you believed; Drip then Expand; dry-season arguments; the aquifer; voted lens versus satisfied lens) belong to the two-week review, the cold debrief with the record in hand.
- **Surveys.** Pre (before the session, own phone): fairest rule for sharing scarce water (forced choice, neutral wording, one sentence why); rank equity, efficiency, sustainability; protect the river before any farm (5-point); ten knowledge items, two per learning outcome 1–5, in two parallel forms A and B assigned at random, piloted on students from a previous cohort rather than on colleagues. Immediate post (paper, end of session, keyed in by the facilitator): the fairness item again, "did the shortage feel real", one free line — not the knowledge items, which would measure the debrief. Delayed post (two-week review, own phone): the other knowledge form, the fairness item, the ranking. All three joined by the linking code.
- **Review form**: journey map (optional); "I like / I wish / What if" × 3; two numbers checked against sources, the four scientific questions, one recommendation naming who loses.

### 5.4 Accessibility, localisation, robustness

WCAG 2.1 AA contrast; numbers ≥ 14 px (16 px, 1.5 line height for Devanagari and Ethiopic, fonts subset); targets ≥ 48 px; `prefers-reduced-motion` end states; screen-reader focus moves to the role button at each hand-over with the role announced; `aria-valuetext` on the stepper in Mm³ and points; timers from timestamps with a Wake Lock for the session (Screen Wake Lock API needs iOS 16.4+; older iOS falls back to a facilitator reminder); no haptics on iOS Safari (`navigator.vibrate` is unsupported), so every haptic cue has a visual twin; the room-mode QR carries only a short-lived upload token, never game state; confirm or 3 s undo on Commit and Close the vote; battery warning at 20 %; export to a second phone offered after every season carries public projections and the encrypted private payloads only, so a mid-game export cannot leak who pumped. Amharic and Hindi are left-to-right; a right-to-left locale would need a decision on the upstream-left river convention.

## 6. Data specification

Two documents define a game: the scenario (what the world is) and the Season Record (what happened). Both are JSON, versioned, validated against JSON Schema (`schema/scenario.schema.json`, `schema/record.schema.json`). A game is fully reproducible from the two.

### 6.1 `scenario.json`

```markdown
{
  "schemaVersion": "3.0",
  "id": "default-basin", "name": "Fairflow default basin",
  "provenance": { "kind": "example" | "builder" | "pipeline", "createdBy": "role or facilitator", "createdAt": "ISO-8601", "basedOn": null },
  "basin": {
    "inflow": { "wet": 22, "normal": 17, "dry": 12, "unit": "Mm3/season", "dryDrift": 0, "source": "..." },
    "deck": { "wet": 1, "normal": 3, "dry": 2 },
    "reserve": { "value": 2, "mode": "absolute" | "fraction", "source": "..." },
    "aquifer": { "initial": 20, "reserve": 5, "lowThreshold": 10, "naturalRecharge": 1.0, "surplusRecharge": true, "returnFlows": true,
                 "gwSwCoupling": { "enabled": true, "maxInflowLossMm3": 1.0 }, "seatCostMultipliers": [1.0, 1.5, 2.0], "source": "..." },
    "gameLength": { "min": 5, "max": 6 }
  },
  "schemes": [ { "id": "A", "name": "Orchard Estate", "seat": 1, "shape": "circle", "glyph": "pomegranate",
      "areaHa": 625, "crop": "pomegranate", "method": "drip", "depthMm": 1000, "beta": 0.90, "yieldTHa": 8.0, "ky": 0.8,
      "people": 81, "peopleUnit": "employees" | "households" | "dependants", "kappa": 1.0, "price": 1.0,
      "derived": { "demandMm3": 6.25, "capacityT": 5000, "wpKgM3": 0.80 },
      "privateGoal": { "kind": "livelihood_share", "threshold": 0.75 },
      "card": { "situation": "...", "knows": ["...", "..."] },
      "fields": { "areaHa": { "source": "...", "entered": "example" | "user" | "assumed", "outOfRange": false } } } ],
  "lenses": [
    { "id": "utilitarian", "rule": "max_value", "plainName": "Biggest harvest", "enabled": true },
    { "id": "weighted_utilitarian", "criterion": "capacity/demand", "enabled": false },
    { "id": "egalitarian", "criterion": "1", "plainName": "Same for each" },
    { "id": "proportional", "criterion": "demand", "plainName": "Same share of need" },
    { "id": "capability", "criterion": "people*kappa", "plainName": "Per person" },
    { "id": "sufficientarian", "floor": 0.5, "floorScaling": "proportional" | "cea", "secondary": "max_value" | "prioritarian" | "proportional", "plainName": "Enough first" },
    { "id": "prioritarian", "criterion": "weight^(1/gamma) * demand^((gamma-1)/gamma)", "params": { "gamma": 2, "weight": "1" | "people" }, "enabled": false },
    { "id": "equal_sacrifice", "rule": "cel", "enabled": false }, { "id": "talmud", "rule": "talmud", "enabled": false } ],
  "defaultLens": "proportional",
  "actions": { "orchard": { "cost": 10, "demandFactor": 1.3, "priceFactor": 2, "lag": 1, "oncePerGame": true },
               "drip": { "cost": 8, "demandFactor": 0.8, "betaAfter": 0.90, "oncePerGame": true },
               "expand": { "cost": 5, "areaFactor": 1.2, "demandFactor": 1.2, "capacityFactor": 1.2 },
               "pump": { "cap": 2, "costBase": 2, "costSlope": 6, "rationing": "pro_rata" } },
  "modules": { "M2": false, "M3": false, "M4": false, "M5": false, "M6": false },
  "moduleParams": { "M2": { "stealFine": 6, "rotationLoss": 0.5 }, "M3": { "budgetPerSeason": 5, "monitor": 5, "lining": 15, "dam": 20, "audit": 3, "conveyanceLoss": 0.2, "seepageRecharges": true, "damCapacity": 3 },
                   "M4": { "deck": ["pest", "delayed_rains", "outgrowers", "riparian_recharge", "groundwater_crisis", "subsidy", "price_spike", "basin_plan"] }, "M5": { "reserveRaise": 3, "breachPenalty": 0.9 } },
  "indicators": { "equityBands": [0.75, 0.90], "adequacyBands": [0.68, 0.80], "efficiencyBands": [0.85, 0.95], "sustainabilityBands": [1.00, 1.15], "r3Ramp": 0.6,
                  "survivalFloor": 0.5, "equalisandum": "claimant" | "hectare" | "person", "efficiencyBasis": "consumed" | "diverted", "collectiveScore": "geometric" | "daly_cap" },
  "session": { "negotiationS": { "seasons0to2": 180, "from3": 240 }, "decisionS": 45, "handoverStartsTimer": true,
               "season0Minutes": 10, "timeboxMinute": 80, "deliberation": "table" | "person" | "none", "plannedMinutes": 120 },
  "spatial": { "kind": "schematic" | "geojson", "geojson": null, "unitAttributes": null },
  "treatments": { "silentMode": false, "universalisationNudge": false, "secretBallot": false, "authorityHandoverSeason": 2 }
}
```

**Lens `criterion` grammar.** Criterion strings are not free-form JavaScript. Operands are the per-scheme fields `1`, `demand`, `capacity`, `people`, `kappa`, `area`, `price`, `prevAdequacy` and the lens parameters named in `params`; operators are `+ - * / ^` and parentheses; no function calls, no comparisons, no access to state outside the scheme row. The parser (a 60-line Pratt parser in the engine) rejects anything else at scenario-load time with a named error, so a Builder-authored lens can never crash or leak. The Builder reports which classical rule a user expression reduces to by evaluating it on the default basin and matching §3.1.

Schema rules: every player-editable numeric leaf is wrapped in `fields` with `source`, `entered`, `outOfRange`; derived values are recomputed on load and must agree; `peopleUnit` must be one value across schemes or the Builder flags the mix; inflows are stored as absolute values, never as factors; unknown module flags are errors; migrations are code (`2.0 → 3.0` converts factors to absolute inflows and adds `beta`, `peopleUnit`, `session`).

### 6.2 Season Record

Append-only; state = `events.reduce(applyEvent, initialState(scenario))`. Every event: `seq`, `t` (ISO-8601 device time), `season`, `actor`, `type`, typed `payload`, `visibility` (`public` | `self` | `sealed`). Every numeric field is rounded to 1e-6 when the event is created. The scenario is embedded at `game.created`.

| type | visibility | payload |
| --- | --- | --- |
| game.created | public | gameId, scenario, mode, gameLength (SHA-256 commitment over a secret nonce), deckOrder (commitment), appVersion, engineVersion |
| treatment.assigned | public | silentMode, universalisationNudge, secretBallot, authorityHandoverSeason, deliberation, assignedBy (facilitator \| random), randomisationSeed? — written before season 1 so analysis can recover arm membership |
| linking.code | self | role, code (participant-generated, e.g. mother's initials + birth month) — links pre-, post- and delayed-post surveys without identity; never stored with a name |
| player.joined | public | role, deviceId (salted hash), consentGiven, presurveyComplete (both before the role was shown; the answers themselves live in `surveys.csv`, not the record) |
| authority.handover | public | from, to, season |
| season.climate | public | card, inflow (after any GW–SW reduction), reserve, allocable, eventCard? |
| lens.proposed | public | lens, proposer, msSinceOpen |
| lens.voted | public | lens, voter, msSinceOpen |
| lens.chosen | public | lens, tally, tieBreak?, veto?, revote?, byTimeout |
| allocation.issued | public | lens, Q\[\], loss\[\] \[M3\], rotation? \[M2\], surplusToAquifer |
| handover.accepted | public | role, msSinceCommit (hand-over latency) |
| prediction.answered | public | role (the predictor), metric, predictedValue, actualValue filled at `season.resolved` |
| action.played | sealed | role, tokens \[{type, n}\], pumps, steal? \[M2\], cost, committedAt, autoCommitted |
| authority.acted | public | action, cost, budgetAfter \[M3\] |
| event.drawn | public | cardId, effect |
| season.resolved | mixed | public: pumpsTotal, ePJ, eSE {claimant, hectare, person}, giniStar, F {consumed, diverted}, S, aquifer, inflowNext, ecosystem?, welfare {UWF, PWF, SWF, EWF, CWF}, verdict {voted, satisfied, pumpingGap}, cropFailureFlag, coreStable?; sealed: W\[\], A\[\], Y\[\], dL\[\], L\[\], pumpsBy\[\], cropFailure\[\], shapley? |
| game.timeboxed | public | firedBy (facilitator), atSeason, sessionMinute — play ends after the current season; T is still unsealed and the hash still verifies |
| game.ended | public | T, nonce, deckOrder revealed, truncated, collectiveScore, cropFailureFlag, goals\[\] |
| debrief.opened | public | perPlayer (true \| false) — the moment sealed fields become readable; perPlayer false keeps pumpsBy sealed in every projection |
| debrief.note | public | promptId, role? (null for a table rule), text |
| review.answer | self | part, item, value |
| agent.rationale | sealed | role, text (v2.0) |

Pre-, immediate-post and delayed-post survey answers are not record events; they are rows in `surveys.csv` keyed by linking code, `phase` (`pre` | `post` | `delayed`) and `form` (A | B), so a record can be shared for replay without carrying survey data.

**Sealing.** Commitments at creation, revealed at `game.ended`. In **table mode** the single device holds sealed fields in its IndexedDB and every projection, export and screen before `debrief.opened` omits them. In **room mode** the relay runs the engine and is the only holder of sealed fields: phones send *intents* (`pump 2`, `play drip`), the relay validates, sequences and applies them, stores the record, and sends each phone its own role's `self` projection plus the public views. Sealed data never leave the relay until `debrief.opened`, so there is no client-side key to manage and a reconnecting host learns nothing. (v2 proposed client-side encryption of `pumpsBy` and `action.played`; the technical review showed that host failover requires the full log and the key on every potential host, which breaks the promise. The relay-runs-the-engine design replaces it.) Public projections `view.season`, `view.map`, `view.reveal`, `view.debrief` are derived only from `public` fields, plus `sealed` fields after `debrief.opened` if `perPlayer` allows.

### 6.3 Export and anonymisation

Exports: `record.json` (full, sealed fields present only after `debrief.opened`), `seasons.csv` (one row per season, all public dials; per-scheme columns after the debrief), `events.csv` (one row per event with payload flattened; the file every §10 hypothesis needs), `surveys.csv` (by linking code and phase), `codebook.md` (generated from the schemas). Roles, never names; device ids hashed with a per-game salt destroyed after the course; linking codes hashed with a per-cohort salt before research export; free text filtered before research export; treatment arm read from `treatment.assigned`, never inferred. Research dataset = the four CSV files concatenated across games with `gameId`, `scenarioId`, `mode`, `cohort`; schema frozen at v2.0.

## 7. Software architecture

One pure engine, several thin shells. The engine knows nothing about screens, networks or phones; every shell feeds it events and renders its projections, and every service reads or relays the Season Record. Nothing but the engine computes a number, and the same engine code runs on the phone, on the room relay and in the CI harness.

&#91;embedded content: architecture · 4 shells, 1 engine with its record, 4 services\]

Shells render projections and submit intents; the engine validates and applies them; the record stores them with a visibility class per field; services consume the record offline or relay it between devices.

### 7.1 Modules

| Module | Stack | Responsibility | Release |
| --- | --- | --- | --- |
| `@fairflow/engine` | TypeScript, no DOM, seeded RNG | `initialState`, `applyEvent` (total: returns state or a typed rejection, never throws), `allocate` (claims-problem solver with weights, floors, maximiser), `resolveSeason`, `indicators`, `welfare`, `verdict`, `stability`, `criterion` parser; projections `view.season / map / reveal / debrief / self(role)` derived only from fields the visibility class allows; `debriefBrief(record)`; NDJSON worker mode (`engine serve`) for harnesses and the relay | v1.0 |
| `@fairflow/schema` | JSON Schema + TS types | scenario and record validation, migrations (2.0 → 3.0) | v1.0 |
| `@fairflow/scenarios` | JSON | default, Balotra, Mwea (Omo read-only from v1.1), every parameter with `source` | v1.0 |
| `@fairflow/ui` | React + TypeScript + Vite, PWA plugin; headless kit (Radix or shadcn on Tailwind) for forms, sheets, tabs, modals; no charting library | the screens of §5.2; about 30 components, ten hand-written SVG/CSS: map, share-bars, two-needle gauge, triangle stack, tank, stepper, timer ring, hand-over, polygon fill, season tabs; design tokens for shapes, glyphs, band words, type scale | v1.0 |
| `@fairflow/store` | TypeScript, Dexie (IndexedDB) | append-only event store, export, import, replay; Wake Lock; timestamp timers; sealed-field redaction on export before `debrief.opened` | v1.0 |
| `@fairflow/builder` | React | Scenario Builder (default-basin editing in v1.0, full stepper with sourcing guide in v1.1) with live allocation table | v1.0 / v1.1 |
| `@fairflow/relay` | Node, `ws`, imports `@fairflow/engine`; EU host | room codes (five characters); receives intents, validates and sequences with the engine, stores the record, sends each client its role projection and the public views; big screen is a dumb display that reconnects; role token in `localStorage` for reconnection; if the venue network dies the host exports and the table continues in table mode | v1.1 |
| `fairflow-balance` | Python harness over `engine serve` | strategy agents, Monte Carlo over decks and lengths, pass criteria and sensitivity report, three CI tiers | v1.0 |
| `fairflow-pipeline` | Python notebooks (WaPORDL, WaPORIPA, mapshaper) | GeoJSON simplification, zonal statistics, `scenario.json` writer; runs offline, ships outputs only | v1.2 |
| `fairflow-agents` | Python, Concordia | personas, game-master wrapper over the engine, synthetic cohorts, seat-filling service | v2.0 |

v2 specified `@fairflow/sync` as a host-device sequencer over Supabase Realtime with client-side encryption. The technical review showed the design contradicted itself (failover needs the full log and the key on every potential host), and that Supabase Realtime gives no authoritative sequencer without rebuilding one in Edge Functions. The relay above replaces it; Supabase remains an option for hosted persistence of research records if data residency allows.

### 7.2 Engine contract

- Pure functions; arithmetic in Mm³, t and points as floats; every number rounded to 1e-6 at the event boundary; display rounding is the shell's; tests compare to two decimals and the replay test compares byte-for-byte.
- RNG seeded from a secret nonce; deck order and length drawn at creation and committed by SHA-256; the nonce is revealed at `game.ended`.
- `applyEvent` enforces visibility: a projection for role r contains only `public` fields and r's own `self` fields until `debrief.opened`.
- Projections are derived, never stored; the privacy projection test (§9.1) runs on every build against every projection and every export path.
- `engine serve` reads NDJSON commands on stdin (`init`, `apply`, `view`, `resolve`) and writes NDJSON results; one process handles thousands of games.
- Published as a package; EquiNex's Policy Simulator imports `allocate` and `welfare`.

### 7.3 Persistence and offline

Service worker precaches the shell, scenarios and subset fonts; IndexedDB writes each event as it happens (a crash loses at most the current unresolved event); export via Web Share API and QR (an upload token, never state); a record is under 200 kB. Wake Lock where supported (iOS 16.4+), facilitator reminder otherwise.

### 7.4 Budgets

| Budget | Target |
| --- | --- |
| First load | < 2 MB, < 3 s on 4G |
| Season resolve | < 50 ms on a 2019 mid-range Android; < 10 ms in `engine serve` |
| Map redraw | < 16 ms schematic; < 200 ms GeoJSON ≤ 300 polygons |
| Relay | < 150 ms intent-to-projection round trip on venue Wi-Fi; 40 phones per room |
| Browsers | iOS Safari 16.4+, Android Chrome 110+, desktop Chrome and Firefox current |
| Screen | 360 × 640 minimum, portrait first; big-screen view optional (v1.1) |
| Accessibility | WCAG 2.1 AA; band by position and word; focus management on hand-over; no haptic-only cue |
| Localisation | strings in resource files; English v1.0; Amharic and Hindi v1.2 with 16 px minimum and subset fonts |

### 7.5 Licensing, repositories and open-source structure

Fairflow is an open-source contribution from the first tag, not a project opened later. The structure below is part of the build contract.

**Repositories** (GitHub organisation `fairflow-water`, where EMODPS-ogb3 already lives):

| Repository | Contents | Licence | First tag |
| --- | --- | --- | --- |
| `fairflow-water/fairflow` | Monorepo: `packages/engine`, `schema`, `scenarios`, `ui`, `store`, `builder`, `relay`; `docs/` (this blueprint as `docs/blueprint.md`, exported from the living document at each tag; `docs/research.md` linking the OSF pre-registration; `docs/decisions/` as ADRs, one per §12.2 row and per cohort-cut decision); `content/` (role cards, lens cards, scripts, surveys) | MIT for code; CC BY 4.0 for `docs/` and `content/` | v1.0 |
| `fairflow-water/fairflow-balance` | Python harness, strategy agents, criteria, sensitivity reports | MIT | v1.0 |
| `fairflow-water/fairflow-pipeline` | WaPOR notebooks and GeoJSON writer; separate because of the GPL boundary | MIT for the writer; the WaPOR notebooks keep their GPL-3.0 and only their outputs ship | v1.2 |
| `fairflow-water/fairflow-agents` | Concordia personas, game master, seat-filling service | MIT; Concordia Apache 2.0 server-side | v2.0 |
| `fairflow-water/fairflow-data` | Research datasets per cohort, frozen export schema, codebook; released only after ethics approval and anonymisation review | CC BY 4.0 | first approved cohort |

**Licences, split by what the thing is.** Code is MIT, as EMODPS-ogb3 already is. The blueprint, cards, facilitator script and survey instruments are teaching materials and are CC BY 4.0, so other lecturers can adapt them to their own basins with attribution. Scenario files and fixtures are CC BY 4.0 with their `source` strings as the attribution trail, which the schema already enforces. Participant data are never in a code repository; they are released per cohort from `fairflow-data`. No GPL code in the app bundle.

**Metadata at the first tag (cheap now, expensive later).** The v1.0 tag ships with: `LICENSE` (MIT) and `LICENSE-docs` (CC BY 4.0) at the repository root, with the split stated in `README.md`; an SPDX licence-identifier header (MIT or CC-BY-4.0) on every source and content file, checked in CI by a REUSE-compliance job so the dual licence is unambiguous file by file; `CITATION.cff` naming the engine, the blueprint, and the three source studies, with a Zenodo integration so every tag receives a DOI; `CONTRIBUTING.md` restating §8.5 (a parameter change is a PR that updates the scenario, its `source`, the fixtures and re-runs the balance baseline); `GOVERNANCE.md` (maintainer; a science-reviewer role for anything touching §2; no scenario ships without sources) and a Contributor Covenant code of conduct, because this is a classroom tool.

**What is held back, and until when.** The Balotra scenario numbers come from Sharma et al. (in prep.): the default basin and Mwea ship at v1.0, Balotra when that paper is out or with the co-authors' written agreement. The pre-registration lives on OSF and is linked, not copied. Pilot records (`provenance.kind = "pilot"`) are public; cohort records wait for anonymisation review.

**Publication plan.** A *Journal of Open Source Software* paper on `@fairflow/engine` is submitted at the v1.1 tag: short, peer-reviewed, citable, and the review is a free code audit of the claims solver, the welfare functions and the privacy projections. Its scope is the engine and the balance harness, not the game's learning claims. The serious-game paper (design, the metric-is-a-lens result, cohort evidence) goes to *Simulation & Gaming* or *HESS* once two cohorts exist, as §10 requires; the engine paper is cited from it so the methods are already reviewed.

## 8. Technical development roadmap

Team: two developers (engine and data; UI) and one domain lead (content, pilots, science review, ethics). Work is organised in epics with explicit dependencies; v1.0 is planned to the day because the first cohort date is fixed, later releases to the week.

### 8.1 Epics and dependencies

| Epic | Contents | Depends on | Release |
| --- | --- | --- | --- |
| E1 Engine core | claims solver (all rules), criterion parser, production, indicators, aquifer with β and r₀, welfare, verdict, debrief brief, both fixture sets, property tests, `engine serve` | — | v1.0 |
| E2 Schema and scenarios | JSON Schemas (3.0), migrations, default and Balotra and Mwea scenarios with sources | E1 | v1.0 |
| E3 Event store and replay | IndexedDB store, visibility classes, sealed commitments with nonce, export/import with redaction, replay, projections | E1, E2 | v1.0 |
| E4 Core screens | header with tank, S3 map, S4 share-bar vote with polygon fill and per-season timer length, hand-over and S6 with prediction tap, S7 three-beat reveal, S8 with brief and time-box | E1, E3, design tokens | v1.0 |
| E5 Onboarding and debrief | season 0 as engine mode, S2 pre-session QR flow and join by linking code, S9 season tabs and gauge with equalisandum and F toggle, S10 review, printed facilitator script with time-boxes | E4 | v1.0 |
| E6 Builder (reduced) | default-basin field editing, example chips, live allocation table, save | E1, E2 | v1.0 |
| E7 PWA and robustness | service worker, offline, Wake Lock with fallback, timestamp timers, interrupted-state recovery, undo | E4 | v1.0 |
| E8 Balance harness | strategy agents over `engine serve`, criteria, sensitivity, three CI tiers | E1 | v1.0 |
| E9 Content | role cards, lens cards, read-back templates, surveys in two forms and knowledge items, deliberation sheet, player guide, facilitator script, consent text | domain lead; E2 | v1.0 |
| E10 Relay and room mode | `@fairflow/relay` running the engine, intents, role projections, reconnection, big screen, S11 with time-box, table-mode fallback | E3 | v1.1 |
| E11 Modules 2–5 and extra lenses | rules, balance runs, screens for Steal, Authority investments (with the lining-paradox card), events, River seat; full welfare table | E1, E8 | v1.1 |
| E12 Full Builder and Omo example | stepper, sourcing guide, import, share, user-defined lenses, Omo read-only | E6 | v1.1 |
| E13 Pipeline and real geography | WaPORDL + WaPORIPA notebooks, GeoJSON presets, Leaflet layer, ET-scaled demand option, reproduction of the papers' indicators | E2 | v1.2 |
| E14 Omo policy cards, M6, treatments, localisation | Pareto cards from EMODPS-ogb3, side payments, silent mode, nudge and secret ballot, Amharic and Hindi | E11, E12 | v1.2 |
| E15 Agent layer and research freeze | Concordia personas and game master, seat filling, synthetic cohorts, export schema freeze, EquiNex integration | E10, E8 | v2.0 |

### 8.2 v1.0 sprint plan (four weeks, day by day)

| Week | Day | Engine and data (Dev A) | UI (Dev B) | Domain lead | Gate |
| --- | --- | --- | --- | --- | --- |
| 1 | Mon | Repo, CI, package layout, schema 3.0 skeleton | Design tokens (shapes, glyphs, band words, type scale), header with tank | Personas from interview themes; ethics protocol submitted (pre-session QR survey, linking code, delayed post-test) |  |
| 1 | Tue | Claims solver with all rules and the criterion parser; allocation fixtures green | S0, S2 shells; schematic map SVG | Role-card drafts (≤ 120 words, people unit stated) |  |
| 1 | Wed | Production, indicators (both equity metrics, F consumed and diverted, S with β), aquifer with return flows, r₀, coupling, rationing; **β fixture set generated** | Share-bar lens row; two-needle gauge component | Lens-card fronts and backs; plain names and "who gets more" templates |  |
| 1 | Thu | Welfare, verdict with EDE scaling, debrief brief, property tests, `engine serve` | Triangle stack; timer ring and bar with per-season length | Default, Balotra, Mwea scenarios with sources; paper cards printed; deliberation sheet drafted |  |
| 1 | Fri | Both fixture sets complete; `engine serve` drives a scripted game | Paper-pilot support: engine output on a laptop | **Paper pilot**: two tables, season 0 plus three seasons, timed by block; test share-bars, pump-as-borrowing, three-beat reveal, the deliberation sheet | Engine green; season 0 ≤ 10 min, seasons ≤ 11 min, a comprehensible first vote — or redesign the lens UI before Tue |
| 2 | Mon | Event store (Dexie), visibility classes, applyEvent wiring, nonce commitments | S3 climate and map wired to engine | Revise cards from pilot; read-back templates |  |
| 2 | Tue | Export/import JSON and CSV with redaction, replay, byte-identical test | S4 vote with chips, tally, veto modal, polygon fill, timeout-to-previous-lens | Knowledge items drafted, two per LO, forms A and B |  |
| 2 | Wed | Privacy projections and test over every projection and export path; rejection coverage | Hand-over screen with prediction tap and S6 private turn with stepper, tank motion, hold-to-commit | Facilitator script v1 (paper) with phase time-boxes |  |
| 2 | Thu | Balance harness skeleton over `engine serve`; baseline tier in CI | S7 three-beat reveal, read-back | Player guide draft |  |
| 2 | Fri | Full scripted game through the store, including a time-boxed one | S8 game end with brief, time-box and the reveal-who-pumped choice; season 0 mode | Two colleagues play one season on the phone | A season end to end on a phone |
| 3 | Mon | Balance agents, criteria, sweep on three scenarios; tune pump cost if needed | S9 debrief: season tabs, gauge, equalisandum and F controls, predictions, sheet | Knowledge items piloted on six students from a previous cohort, not colleagues |  |
| 3 | Tue | Store hardening; interrupted-state recovery (background, lock, reload) | S10 review form; S2 pre-session QR flow and join by linking code | Consent text final; QR survey live |  |
| 3 | Wed | Builder data layer: field model with source, range, provenance, people unit; live allocation table | S1 reduced Builder UI | Facilitator script v2 with branches and the safety norm |  |
| 3 | Thu | PWA: service worker, precache, Wake Lock with fallback, timestamp timers | Accessibility pass: focus management, reduced motion, 48 px targets, band words, visual twins for haptics | Player guide final |  |
| 3 | Fri | Replay-diff CI job | Undo toasts, battery warning, redacted export-after-season | **App pilot 1**: one table, full 120-minute timetable, timed by block | Full game played, exported, replayed on a phone of the other platform; balance baseline met; play ≤ 80 min, session ≤ 120. **Cohort-cut decision (§8.3)** |
| 4 | Mon | Fix list from pilot 1 | Fix list from pilot 1 | Debrief and deliberation rehearsal with script |  |
| 4 | Tue | Performance budgets measured on a 2019 Android and an iPhone | Copy pass against word budgets | Role and lens copy final against sources |  |
| 4 | Wed | Cross-platform replay test; privacy test on every screen | Localisation scaffolding (strings in resources only) | **App pilot 2**: second table, full timetable |  |
| 4 | Thu | Release candidate; fixtures, sensitivity report and privacy report attached | Release candidate | Facilitator log consolidated; open questions closed |  |
| 4 | Fri | v1.0 tag | v1.0 tag | Session plan for the cohort; pre-session QR sent; course-only fallback if ethics approval pending; LICENSE, LICENSE-docs, CITATION.cff, CONTRIBUTING, GOVERNANCE and code of conduct committed; REUSE job green; Zenodo DOI minted on the tag | Definition of done §1.5 |

### 8.3 Effort and the cohort cut

Two independent technical estimates put v1.0 (E1–E9) at 32–36 developer-days against the 40 available to two developers in four weeks — feasible, but with no slack for a redesign after the paper pilot. The plan therefore names a **cohort cut**: features that ship in v1.0 only if the week-3 pilot passes on schedule, and otherwise move to v1.1 without the first cohort losing a learning objective.

1. GeoJSON import path (schematic map only for cohort 1).
2. Export to a second phone during play (the facilitator exports after the session).
3. Hindi and Amharic string scaffolding (English only).
4. Talmud and equal-sacrifice lenses in the engine (disabled by default anyway; fixtures stay).
5. Replay-diff CI job (the replay test still runs on every merge).
6. The F consumed/diverted toggle on S9 (the facilitator reads both numbers from the brief instead).

Nothing in the core loop, the Season Record, the privacy projections, the time-box, the debrief brief or the deliberation sheet is cut. The week-3 app pilot is the decision point and the decision is recorded in the repository.

### 8.4 Release train

&#91;embedded content: release train · 4 releases, 26 weeks, 4 gates\]

Each gate is a decision, not a date: a release that misses its gate holds, and the next one starts on the parts that do not depend on it. No gate depends on a research result.

| Release | Weeks | Epics | Gate |
| --- | --- | --- | --- |
| v1.0 | 1–4 | E1–E9 | §1.5 |
| v1.1 | 5–9 | E10–E12 | room mode passes the same 120-minute timetable and privacy test as table mode on two pilot tables; balance for every module; v1.0 cohort data exported cleanly; JOSS paper on the engine submitted at the tag |
| v1.2 | 10–16 | E13–E14 | pipeline reproduces Cherry 2025 Table 4-9 and the Balotra village indicators |
| v2.0 | 17–26 | E15 | agents complete 100 unattended games with no engine rejection; agent rationales logged; export schema frozen |

### 8.5 Engineering practice

- Trunk-based development; every merge runs fixtures (both sets), property tests, privacy projection test, schema validation, the replay test, and the baseline balance tier on changed scenarios; the sweep tier runs nightly and the release tier at every tag (§9).
- A parameter change is a pull request that updates the scenario, its `source`, affected fixtures, and re-runs the balance model; the domain lead signs off card copy against sources before each pilot.
- Pilots are ordinary records with `provenance.kind = "pilot"`, excluded from research export.
- Definition of ready for a screen: layout zones, number budget, copy budget, acceptance test and empty/error/interrupted states written in §5.2 before the ticket opens.

## 9. Verification and validation

### 9.1 Engineering tests (CI on every change)

- Fixtures of §3 (both sets) to two decimals; property tests by random scenario: allocations sum to min(AW, ΣD); no Qᵢ > Dᵢ; proportional gives equal adequacy; strict egalitarian = CEA; equal sacrifice = CEL; Talmud = CEA on half-claims when AW ≤ ½ΣD; prioritarian → equal shares as γ → 1 and → proportional as γ → ∞; the greedy maximiser is never beaten by 10,000 random feasible allocations (optimality check, since the survival branch makes the function non-concave below A = 0.5); E\_PJ = 1 for proportional and E\_SE(claimant) = 1 for equal shares when uncapped; per-hectare E\_SE = E\_PJ in uniform-depth basins; F = 1 at full demand; S > 1 iff ΣP > r₀ in a season with no surplus; aquifer mass balance closes to 1e-6 every season; a criterion string outside the grammar is rejected at load.
- Replay invariance: `reduce(applyEvent)` over an export reproduces every `season.resolved` byte for byte, and the same record replayed under Node (V8) and under WebKit (JavaScriptCore, via Playwright) produces identical `seasons.csv`.
- Privacy projection: with any non-zero pump, no `public` projection, no pre-debrief export and no relay message to a client other than the acting role contains Wᵢ, Aᵢ, Yᵢ, ΔLᵢ or Pᵢ; the S3, S4, S7, S8 and S11 renderers consume public projections only; `debrief.opened {perPlayer: false}` keeps `pumpsBy` out of every projection including S9.
- Rejections: every impossible event returns a typed rejection and leaves state unchanged; a `game.timeboxed` at any point yields a valid, verifiable `game.ended`.
- Commitments: revealed nonce, T and deck hash to the sealed values.
- Rendering: every screen at 360 × 640 with 14 px minimum and 48 px targets, with and without colour, with reduced motion; every haptic cue has a visual twin (checked by a test that runs with `navigator.vibrate` undefined).

### 9.2 Balance model

A Python harness drives the TypeScript engine as a long-lived worker over NDJSON (`engine serve`) — never a port, and never one process per game: six compositions × 2 decks × 2 lengths × 2,000 games is roughly 48,000 games per scenario, and the full ±30 % one-at-a-time sweep over §2.2's \~25 parameters is about 2.4 million games per scenario, roughly 20 CPU-hours in-process. Strategy agents: selfish, principled-X (one per lens), conditional cooperator, floor-seeker, rule-based Authority. Agents are balance stereotypes, not calibrated humans.

Three tiers: **baseline** on every merge (the shipped scenarios, 200 games per cell, about eight minutes in-process); **sweep** nightly (±30 % one-at-a-time over every §2.2 parameter, 500 games per cell); **release** before each tag (full 2,000 games per cell plus pairwise interactions for β, r₀, pump cost and reserve). A merge is blocked only by the baseline tier; sweep and release regressions open issues.

| Criterion | Threshold | Why |
| --- | --- | --- |
| Lens matters | dry-year range of E\_PJ across lenses ≥ 0.4; Q range ≥ 40 % of demand for at least one scheme | the learning goal needs visible differences |
| Cooperation rewarded | all-principled tables end with B\_T ≥ 0.5 B₀ in ≥ 90 % of games |  |
| Dilemma bites then costs | pumping is individually profitable in ≥ 80 % of deficit seasons while B > B\_low, and unprofitable for at least two of three seats once B < B\_low; all-selfish tables reach B\_res by season 5 in ≥ 80 %, not before season 3 in ≥ 90 % | the intended shape: rational early, ruinous late (§3.4) |
| No dominant lens | no lens tops the collective score in > 60 % of mixed games | the vote is not trivial |
| Goals attainable | every R15 goal is met by its scheme in ≥ 50 % of all-principled games without pumping | a goal nobody can reach without defecting teaches defection |
| Rebound reachable | Drip then Expand raises own livelihood and basin use in ≥ 70 % of games where played |  |
| Lining worth buying \[M3\] | lining raises the collective score in ≥ 30 % of games where bought, despite lost seepage recharge | the paradox is a trade-off, not a trap |
| Crop failure rare but possible | 5–30 % of mixed games | the floor bites sometimes |
| Human baselines | no-communication selfish tables near 20–25 % of optimal collective score; principled tables 55–75 % | Ostrom, Gardner & Walker 1994; Balliet 2010 |
| Timing | decisions per season × durations measured in the week-1 paper pilot ≤ 11 minutes; season 0 ≤ 10 |  |

A scenario failing a criterion ships only with the failing criterion shown in the Builder as a warning ("in this basin the lens barely matters").

### 9.3 Pilots

- Week-1 paper pilot: two tables, season 0 plus three seasons, every block timed; vote comprehension (can a player say who gets more under two lenses after one look at the share-bars); the three UX tests (share-bars, pump-as-borrowing, three-beat reveal); the deliberation sheet tried once.
- Week-3 and week-4 app pilots: the full 120-minute timetable with block-level timestamps from the record, facilitator log, think-aloud on one player per table; pilot 1 is the cohort-cut decision point.
- Pass: play ≤ 80 minutes, session ≤ 120, no block more than 20 % over its budget, every player able to state the lens in force and the total pumped at the end of a season.

### 9.4 Data quality

Records validated on export and import; invalid records kept but excluded from research; a CI job replays stored example records and diffs the dials to catch silent engine drift; `truncated` games are kept and flagged, never dropped.

## 10. Research, ethics and data protection

### 10.1 What the first cohort can and cannot show

One cohort of roughly six to eight tables is a descriptive study. It can support feasibility and usability claims (the timetable holds, decision durations, vote comprehension), descriptive learning-process evidence, within-table behavioural descriptives from the log, and reproducibility of results from records. It cannot support a causal claim about the game, a mode, a treatment or a lens. The pre-registration says so; no release gate depends on a research result; and nothing in the blueprint is phrased as if the first cohort will prove anything.

### 10.2 Measures

- **Pre** (own phone, before the session): fairest rule (forced choice among the five principles in neutral wording, one sentence why); rank equity, efficiency, sustainability; protect the river before any farm (5-point); knowledge form A or B (ten items, two per LO 1–5), assigned at random.
- **Immediate post** (paper, end of session, keyed in by the facilitator): the fairness item, "did the shortage feel real" (Peters & Vissers), one free line. Not the knowledge items: a test straight after a scripted debrief that has just shown which principle the scoring vindicated measures comprehension of the debrief, not learning from play.
- **Delayed post** (own phone, two-week review, before the cold debrief): the other knowledge form, the fairness item, the ranking.
- **In-game**: `prediction.answered` (mental-model accuracy per hand-over), `lens.voted` timing, pumping by season and seat, `debrief.note` rules from the deliberation.
- **Review form** (homework) and the Scenario Builder exercise at the two-week review for LO6.

Instrumentation caveat, stated in the pre-registration: the pre-play fairness item asks about abstract sentences; the post-play item asks about principles the student has now seen as *Enough first* and *Biggest harvest* with an hour of experience attached. The wording is identical; the stimulus is not. The switch rate is reported with that caveat and against the stability Cappelen et al. (2007) report for fairness ideals.

### 10.3 Pre-registered exploratory hypotheses (first cohort)

1. Stated lens preference moves toward floor-based principles after a dry-year experience (Frohlich & Oppenheimer predict floor-plus-efficiency as the modal impartial choice).
2. Most students explain the two-metric disagreement correctly at the delayed post-test.
3. Pumping rises in the season after an unequal season (E\_PJ in the poor band).
4. The end-game surge is reduced under the sealed length (no rise in pumping in the last season relative to the one before).
5. Hand-over predictions improve over seasons (absolute error falls).
6. Tables whose deliberation rule is a monitoring or sanction rule had higher total pumping than tables whose rule is an allocation rule (descriptive only).

The comparison condition for a second cohort is *vote* versus *rotating fixed rule* (exposure to every lens without choice), with matched talk time, not a silent fixed-rule arm, which cannot teach LO1 by construction and confounds with silent mode. The unit of analysis is the table.

### 10.4 Ethics and data protection

- **Consent** per person on the pre-session flow, recorded as `consentGiven` in `player.joined`; a game with any role declining is excluded from research export on the device, but is still played and debriefed.
- **Minimal data**: roles not names; participant-generated linking codes, hashed with a per-cohort salt before export; salted device hashes; free text filtered; salts destroyed after the course.
- **Students**: the session may be compulsory; contributing to the research dataset is not, and grades cannot depend on it or on anything said in the debrief. The pre-survey precedes role assignment so the role does not prime the answer.
- **Debrief exposure**: the facilitator speaks the safety norm before `pumpsBy` is unsealed; a table may keep per-player pumping sealed (`debrief.opened {perPlayer: false}`); the deliberation sheet asks for a rule, never for a name.
- **Ethics review**: protocol submitted in build week 1, covering the pre-session survey, the linking code, the delayed post-test and the deliberation sheets; approval before the first cohort is uncertain, so the first cohort is course-only unless approval arrives; the research dataset starts with the first approved cohort.
- **Storage**: records on devices until exported; relay and research server in the EU; pseudonymous under GDPR Art. 4(5).
- **Agents** (v2.0): players told before play when a role is machine-played; rationales shown at debrief.
- **Publication**: the frozen export schema, the engine and the codebook are published with the first paper so results reproduce from records.

## 11. Theoretical grounding and audit trail

A five-strand literature review (political philosophy; welfare economics and inequality measurement; claims problems and cooperative games; behavioural evidence; water economics, agronomy and groundwater), two expert reviews of v1 (game design; UI/UX) and four blind reviews of v2 (serious-game design; software architecture; water science; research methods) shaped this version. The table records what each element rests on and what changed, with the version in which it changed.

| Element | Grounding | Change and version |
| --- | --- | --- |
| Lens set | The lenses are the classical claims-problem rules with philosophical labels (Thomson 2003; Aumann & Maschler 1985) | Cards carry the formal name; generic claims solver (v2); closed criterion grammar for user lenses (v3) |
| Utilitarian | Value maximisation is Kaldor–Hicks and the equimarginal benchmark, not Benthamite utility | Relabelled value-maximising; greedy maximiser replaces the productivity-weighted heuristic, kept as a variant and relabelled a desert rule (v2) |
| Capability | C = people is equal per head; Sen's conversion factors needed | κ parameter (v2); one people-unit enforced by the Builder, mix stated on cards (v3) |
| Sufficientarian | Frankfurt, Crisp, Shields, Casal; human right to water anchors domestic floors only | Configurable secondary rule; agricultural floor documented as convention (v2) |
| Prioritarian | γ is Atkinson's ε; empirical ε in 1–2; resource-prioritarian; γ → ∞ is maximin not Rawls | Default γ = 2; weights explicit; singularity guarded (v2) |
| PWF | EMODPS-ogb3 applies the isoelastic form to the shortfall (decreases in supply) | Atkinson form on supply; error reported; column-wise comparison stated (v2, v3) |
| Equity metrics | 1 − CV passes the standard axioms, is unbounded below, non-prioritarian; equalisandum is a value choice (Sen 1979) | Switchable equalisandum; two-needle gauge; clipping before composites; Gini n/(n − 1) (v2) |
| Efficiency | Economic WP preferred across crops (Molden et al. 2010); first normalisation compressed the dial; consumed vs diverted is the Perry/Grafton distinction | Value-based F relative to design productivity (v2); F on consumed water with a diverted toggle at debrief (v3) |
| Sustainability | Use/recharge = 1 is the global-indicator boundary but the water-budget myth hydrogeologically; return flows are reused | S against renewable supply with good ≤ 1.00; aquifer reserve (v2); consumptive fraction β, natural recharge, return flows, GW–SW coupling, r₃ ramp /0.6 (v2 rev 2.1) |
| Composite | Radar area partially compensatory; three pillars argued as an ordering (Daly, Hoekstra); any composite embeds a lens | Geometric-mean score; triangle as picture; Daly cap as option (v2); scoreboard's own lens named in LO2 and the debrief (v3) |
| FAO-33 | Valid to a 50 % deficit; no Kᵧ for flooded rice or pomegranate; demand is ET-driven | Survival branch documented as convention; Kᵧ flagged (v2); demand not climate-scaled in v1.0, ET-scaled option in v1.2 (v3) |
| Drip | As first written changed nothing (production depends on K and Kᵧ); cuts diversion not consumption | D × 0.8 at constant K (v2); β rises to 0.90 so consumption is visible in S (v2 rev 2.1) |
| Canal lining | Seepage is recharge (Perry et al. 2017) | Lining removes seepage recharge; paradox on the card; balance criterion (v3) |
| Aquifer | Cutting river allocation when the aquifer empties had no physical basis | Seat-dependent pump cost; depletion-scaled cost; pro-rata rationing (v2) |
| Game length | 6–8 seasons exceeded the session and a six-card deck; a seed from the game id seals nothing | 5–6 sealed; deck 1W/3N/2D (v2); secret nonce commitment (v2 rev 2.1) |
| Goals | One trivial, one impossible, one that required pumping; A's 80 % unattainable at 79.8 % | Each attainable without pumping, judged within scheme (v2); A at 75 % with a fixture (v3) |
| Privacy | Per-scheme W on the reveal leaked pumping (W − Q); client-side encryption could not survive host failover | R17 rewritten; public projections only; privacy test (v2); visibility classes on every field; relay runs the engine and holds sealed fields (v3) |
| Determinism | `Math.pow` differs across engines at the last bit | Rounding at the event boundary; cross-engine replay test (v3) |
| Reveal | 22 numbers and three charts could not fit 640 px | Three-beat paged reveal; five numbers per page (v2) |
| Vote screen | 30-number table unreadable at 360 px | Share-bar rows with plain names (v2); timeout rule reconciled with R8 (v3) |
| Debrief | Six typed prompts in 20 minutes is a form, not a debrief; Lederman's phases need safety before disclosure and unused data is wasted | Spoken three-phase protocol on paper; typed prompts in the review (v2); safety norm, predictions read back, engine brief, institution-design deliberation, procedural-justice question (v3) |
| Session | 90 minutes did not close when the beats were timed | 120 minutes; season 0 at 10; negotiation 4:00 from season 3; time-box event; surveys off the clock (v3) |
| Research design | Post-survey was v1.2 while the hypothesis was pre/post; one cohort cannot carry causal claims; one item per LO has no reliability; post-test after the debrief measures the debrief | Both surveys in v1.0 (v2); exploratory pre-registration, two knowledge forms with two items per LO, delayed post-test, linking code, events.csv, no research gates (v3) |
| Build plan | Week 3 overloaded; pilots only in week 4; 32–36 dev-days estimated | Paper pilot week 1; app pilots end of weeks 3 and 4; Builder reduced (v2); cohort-cut list decided at the week-3 pilot (v3) |

Behavioural prediction carried into the design: impartial groups choose "maximise the average with a floor" (25 of 29 groups, Frohlich, Oppenheimer & Eavey 1987); fairness ideals split roughly 44 / 38 / 18 % (Cappelen et al. 2007); communication raises commons cooperation from about a fifth to about three-quarters of optimum (Ostrom, Gardner & Walker 1994; Balliet 2010); the most popular rule can be infeasible against the most powerful riparian (Madani et al. 2014). Unverified items from the review, none of which supplies an engine number: Deutsch 1975; Konow 2003 content; Casal 2007; Young 1988; Ostrom 1990 text; the \~93 % "covenant with a sword" figure; Yaari & Bar-Hillel's 82 %.

## 12. Risks, decisions and references

### 12.1 Risks

| Risk | Likelihood | Effect | Mitigation |
| --- | --- | --- | --- |
| Pumping dominates play | Medium | Lens vote becomes a sideshow | Balance criteria gate release (§9.2 "dilemma bites then costs"); the dilemma is meant to be real; cohort data will show whether it is too real |
| Under-pumping | Medium | No depletion arc, LO4 weak | Students sit face to face and totals are public; B's dry-year goal insurance under egalitarian or utilitarian lenses is the realistic driver and is protected in balance |
| Season runs over 11 minutes | Medium | Play exceeds 80 minutes and eats the debrief | Timers auto-commit; T ∈ {5, 6}; time-box at minute 80; surveys off the clock; paper pilot measures durations before the UI exists |
| Deliberation sheet produces slogans | Medium | LO4 not met | Sheet asks for enforcer and cost, not just a rule; facilitator reads one Ostrom principle aloud as a model |
| Students read the model as a prediction of Balotra or Mwea | Medium | Overclaiming | `assumed` and `example` flags; cards say "stylised"; review asks what the numbers assume |
| A surface leaks private pumping | Medium | The hidden action becomes public | Visibility classes; relay holds sealed fields; privacy test on every projection, export and relay message |
| Pass-the-phone privacy fails socially | Medium | Hidden actions visible | Hand-over screen; norm in the guide; room mode in v1.1 |
| Builder produces unplayable basins | High | Confusion | Hard checks; balance warnings in the Builder; criterion grammar |
| First-vote cognitive load | Medium | Table votes "my column" | Share-bars and plain names; season 0 with two lenses; paper-pilot gate |
| Ethics approval late | Medium | No research data from cohort 1 | Submitted week 1; course-only fallback |
| v1.0 overruns the sprint | Medium | Cohort plays an unfinished build | Cohort-cut list decided at the week-3 pilot; nothing in the core loop is cut |
| Venue network fails (v1.1) | Medium | Room mode stalls | Host exports and the table continues in table mode from the last event |
| Pipeline values differ from the papers (v1.2) | Medium | Credibility | Reproduction gate before any preset ships |
| Agent seat-filling misleads (v2.0) | Low | Trust | Disclosure; rationales at debrief |

### 12.2 Decisions taken in v3

| Question | Reviewer position | Decision |
| --- | --- | --- |
| Session length | Game design and water science: 120 minutes or two sessions; research: separate measurement from debrief | 120 minutes (§5.0); 90-minute fallback defined |
| Pumping attractiveness | Water science: 5.5–6.4 points/Mm³ benefit vs cost 2 → 6.5 may be too attractive | Intended; balance criterion rewritten as "rational early, ruinous late" |
| Room-mode privacy | Technical: client-side encryption cannot survive host failover | Relay runs the engine and holds sealed fields; `@fairflow/sync` dropped |
| Research claims | Research methods: one cohort is descriptive | Exploratory pre-registration; no research gates; delayed post-test; two knowledge forms |
| Demand and climate | Water science: demand should scale with ET | Deferred to v1.2 as a scenario option (every fixture changes) |
| People units | Water science: workers vs households mixed | Stated on cards (v1.0); forced to one unit by the Builder (v1.1) |
| Lining paradox | Water science: lining removes recharge under β | Modelled; stated on the card; balance criterion that lining is still sometimes worth buying |
| Deliberation unit | — | Per table by consensus; per person as a scenario flag |
| Secret ballot | — | Treatment flag for room mode; live tally by default |
| Open-source structure (v3.1) | Author: keep it as an open-source contribution | fairflow-water organisation, monorepo plus satellites; MIT code and CC BY 4.0 content; SPDX headers, LICENSE and LICENSE-docs, CITATION.cff and Zenodo DOI at the v1.0 tag; JOSS engine paper at v1.1; game paper after two cohorts (§7.5) |

### 12.3 Still open

- Hosted persistence of research records: self-hosted EU relay storage versus Supabase (data residency, retention period).
- More than five schemes in the Builder (plurality logic assumes the Authority tie-break; six or more claimants need a run-off rule).
- Omo policy cards from the a priori or the a posteriori EMODPS results, or both.
- Whether the Daly-cap display replaces the geometric mean for advanced scenarios.
- Right-to-left locales and the upstream-left river convention.
- Whether the v1.2 non-stationary deck (`dryDrift`) should be visible to players as a forecast or arrive as a surprise.

### 12.4 References

**Source studies.** Yalew S, Prasad P, Mul M, van der Zaag P (2024) Integrating equity and justice principles in water resources modeling and management, *ERL* 19, 111001, doi:10.1088/1748-9326/ad7a8d · Cherry C (2025) *A framework to analyse efficiency-equity-sustainability trade-offs in irrigated water allocations using remote sensing*, MSc thesis, IHE Delft · Sharma N, Ram B, Yalew S, van der Zaag P, Prasad P (in prep.) Assessing EES trade-offs of interventions in agricultural water management in a semi-arid region in India · fairflow-water (2026) EMODPS-ogb3, MIT.

**Distributive justice and welfare.** Adler 2012 *Well-Being and Fair Distribution* · Adler & Treich 2015 · Aristotle NE V · Atkinson 1970 *JET* 2 · Aumann & Maschler 1985 *JET* 36 · Bentham 1789 · Casal 2007 *Ethics* 117 · Cappelen et al. 2007 *AER* · Crisp 2003 *Ethics* 113 · Deutsch 1975 *J. Social Issues* 31 · Dworkin 1981 *Phil. & Public Affairs* 10 · Frankfurt 1987 *Ethics* 98 · Frohlich, Oppenheimer & Eavey 1987 *BJPS* · Harsanyi 1955 *JPE* 63; 1975 *APSR* 69 · Konow 2000 *AER*; 2001 *JEBO* 46; 2003 *JEL* 41 · Mill 1863 · Mitchell et al. 1993 *JPSP* 65 · Nussbaum 2011 · Parfit 1997 *Ratio* 10 · Rawls 1971 · Sen 1979 Tanner Lecture; 1999 · Shields 2012 *Utilitas* 24 · Thomson 2003 *Math. Soc. Sci.* 45; 2019 *How to Divide When There Isn't Enough* · Young 1987 *Math. Oper. Res.* · Shorrocks 1980 *Econometrica* 48 · Cowell 2011 *Measuring Inequality* · Kot 2020 *Equilibrium* 15 · OECD & JRC 2008 *Handbook on Constructing Composite Indicators* · Munda & Nardo 2009 *Applied Economics* 41 · Neumayer 2013 *Weak versus Strong Sustainability*.

**Water justice, economics and games.** Zwarteveen & Boelens 2014 *Water International* 39 · Syme, Nancarrow & McCreddin 1999 *J. Env. Manage.* 57 · Neal et al. 2014 *Water Policy* 16 · Jepson et al. 2017 *Water Security* 1 · Sultana 2018 *Water International* 43 · UNGA 64/292 (2010); CESCR General Comment 15 · Madani 2010 *J. Hydrol.* 381 · Madani, Zarezadeh & Morid 2014 *HESS* 18 · Mianabadi et al. 2015 *WRM* 29 · Ansink & Weikard 2012 *SCW* 38 · Ambec & Sprumont 2002 *JET* 107 · van den Brink, van der Laan & Moes 2010 TI 10-096 · Dinar & Hogarth 2015 *Found. Trends Microecon.* · Dinar, Rosegrant & Meinzen-Dick 1997 World Bank WPS 1779 · Harou et al. 2009 *J. Hydrol.* 375 · Hu et al. 2016 *Resour. Conserv. Recycl.* 109 · Cullis & van Koppen 2007 IWMI RR 113 · Ostrom 1990 *Governing the Commons* · Ostrom, Gardner & Walker 1994; Ostrom, Walker & Gardner 1992 *APSR* 86 · Balliet 2010 *J. Conflict Resolution* 54 · Janssen, Anderies & Joshi 2011 *Exp. Econ.* 14; Jarke-Neuert 2025 *JESA* · Janssen et al. 2012 *Agricultural Systems* 109; Cardenas, Janssen & Bousquet, field experiments on irrigation dilemmas · D'Exelle, Lecoutere & Van Campenhout 2012 *World Development* 40 · van Klingeren & Buskens 2024 *Rationality and Society* · Aubert, Bauer & Lienert 2018 *EMS* · Medema et al. 2016 *Water* 8 · Hoekstra 2012 *HESS* 16 · Douven et al. 2014 *WRM* 28 · Te Awa Tupua Act 2017 (NZ) · Lederman 1992 *Simulation & Gaming* 23 · Crookall 2010 *Simulation & Gaming* 41 · Peters & Vissers 2004 *Simulation & Gaming* 35.

**Agronomy, hydrology and sustainability.** Doorenbos & Kassam 1979 FAO Irrigation and Drainage Paper 33 · Steduto et al. 2012 FAO Paper 66 · Bouman & Tuong 2001 *Agric. Water Manage.* 49 · Zwart & Bastiaanssen 2004 *AWM* 69 · Molden et al. 2010 *AWM* 97 · Scheierling et al. 2016 *Water Economics and Policy* 2 · Giordano et al. 2017 IWMI RR 169 · Bastiaanssen, Van der Wal & Visser 1996 *Irrig. Drain. Syst.* 10 · Karimi et al. 2019 *Remote Sensing* 11 · Chukalla et al. 2022 *HESS* 26 · Grafton et al. 2018 *Science* 361 · Ward & Pulido-Velazquez 2008 *PNAS* 105 · Pfeiffer & Lin 2014 *JEEM* 67 · Perry 2007 *Irrig. Drain.* 56 · Perry, Steduto & Karajeh 2017 FAO · Berbel et al. 2019 *WRM* 33 · Van der Kooij et al. 2013 *AWM* 123 · Alley, Reilly & Franke 1999 USGS Circ. 1186 · Alley & Leake 2004 *Ground Water* 42 · Healy & Cook 2002 *Hydrogeol. J.* 10 · Gleeson et al. 2012 *Nature* 488 · Gleeson et al. 2020 *Nat. Sustain.* · Wada et al. 2010 *GRL* 37 · Tennant 1976 *Fisheries* 1 · Richter et al. 2012 *River Res. Applic.* 28 · Daly 1992 *Ecol. Econ.* 6 · Malghan 2010 *Ecol. Econ.* 69 · Hoekstra 2014 *WIREs Water* 1 · Roa-García 2014 *Water Alternatives* 7 · Kenya Water Act 2016; South Africa National Water Act 1998.

**Tools.** wateraccounting: WaPORIPA, WaPORMOOC, WAPORWA (github.com/wateraccounting) · Vezhnevets et al. 2023 Concordia (arXiv 2312.03664) · Piatti et al. 2024 GovSim (NeurIPS) · NABARD model scheme, pomegranate · Sangle et al., water requirement of pomegranate, *Annals of Arid Zone* · PhilRice rice labour statistics.

Full citations with DOIs and verification status are in the companion report *Fairflow theory grounding*; the six review reports (v1: game design, UI/UX; v2: game design, technical, water science, research methods) are companion files to this blueprint.

## 13. Change log: v2 to v3

Each row names the finding, which of the four blind v2 reviewers raised it (G = serious-game design, T = software architecture, W = water science, R = research methods; A = author), and where v3 answers it. Findings the author verified numerically are marked ✓.

| # | Finding | Raised by | v3 answer | Where |
| --- | --- | --- | --- | --- |
| 1 | 90-minute box does not close: season 0 needs 8–10 min, 5 + 6×10 + 20 = 85 before surveys and hand-overs | G, W, R | 120-minute session: play ≤ 80, debrief 25, deliberation 15; surveys off the clock; 90-minute fallback | §5.0, R20, §1.5 |
| 2 | Debrief absorbs every overrun | G | Facilitator time-box event at minute 80; `game.timeboxed`; truncated games verify | R20, §6.2, §3.3 |
| 3 | LO4 "institutions that change it" has no mechanic in v1.0 | G | 15-minute institution-design deliberation, one rule per table, recorded in `debrief.note` | §5.0, §1.1 |
| 4 | Scheme A's 80 % goal unattainable without pumping (79.8 % on the cooperative proportional path) ✓ | G | 75 %; attainability fixture; balance criterion "goals attainable" | R15, §3.3, §9.2 |
| 5 | Collective score is itself a proportional-justice lens and the debrief has no line for it | G | Named in LO2 and in the debrief script; Daly cap remains the alternative | §1.1, §2.5 |
| 6 | No safety norm before `pumpsBy` is unsealed; graded peers | G, R | Safety norm spoken first; `debrief.opened {perPlayer}` lets a table keep per-player pumping sealed | R19, §5.3, §10.4 |
| 7 | `prediction.answered` recorded and never used | G | Predictions open the describe phase; logged as a mental-model measure (hypothesis 5) | §5.0, §10.3 |
| 8 | Facilitator is blind to private actions and has three minutes to prepare | G | Engine-generated three-line debrief brief on S8 | §5.0, §5.2 |
| 9 | Timer expiry rule inconsistent between R8 and S4 | G | Previous lens everywhere; `byTimeout` recorded; fixture | R8, S4, §3.3 |
| 10 | Export after every season carries `pumpsBy` in plaintext | G | Visibility classes; redacted export before `debrief.opened` | §5.4, §6.2 |
| 11 | Client-side encryption of `pumpsBy` is theatre while `action.played` travels in clear; host failover needs the key everywhere | T | Relay runs the engine and is the only holder of sealed fields; phones send intents; `@fairflow/sync` dropped | §6.2, §7.1 |
| 12 | `Math.pow` differs between JavaScriptCore and V8; replay not byte-identical | T | Rounding to 1e-6 at the event boundary; cross-engine replay test | §2, §7.2, §9.1 |
| 13 | One process per game for 48,000 games per scenario is infeasible; full sweep is 2.4 M games ✓ | T | `engine serve` NDJSON worker; three CI tiers | §7.2, §9.2 |
| 14 | Expand changes D and K but not area, so E\_SE per hectare and the map drift | T | Expand updates `areaHa`; fixture | §2.2, §3.3 |
| 15 | Lens `criterion` strings undefined; a Builder lens could crash or leak | T | Closed grammar, Pratt parser, load-time rejection | §6.1, §9.1 |
| 16 | Wake Lock needs iOS 16.4+; no `navigator.vibrate` on iOS; QR must not carry state | T | Fallbacks and visual twins; upload-token QR; browser floor raised | §5.4, §7.4 |
| 17 | v1.0 estimated at 32–36 dev-days | T, G | Cohort-cut list of six items decided at the week-3 pilot | §8.3 |
| 18 | Inflow factors 17 × 1.3 = 22.1 ≠ 22 ✓ | W | Absolute inflows stored; migration 2.0 → 3.0 | §2.2, §6.1 |
| 19 | Drip "frees basin water" contradicts Perry/Grafton; no consumptive fraction | W | β per scheme, return flows, F on consumed water with a diverted toggle, S on consumptive use (v2 rev 2.1, consolidated) | §2.1, §2.5, §2.6 |
| 20 | r₃ collapses to zero at 3 Mm³ pumped in a dry year ✓ | W | Ramp /0.6; pumping fixture r₃ = 0.33 | §2.5, §3.3 |
| 21 | Pumping too attractive: 5.5–6.4 pts/Mm³ vs cost 2 → 6.5 ✓ | W | Kept as intended; balance criterion "dilemma bites then costs" makes the shape explicit | §3.4, §9.2, §12.2 |
| 22 | Demand not climate-scaled; depths not crop-specific | W | Stated; ET-scaled option in v1.2 | §2.2, §1.4 |
| 23 | N mixes employees and households | W | Stated on cards; `peopleUnit` field; Builder forces one unit | §2.2, §6.1 |
| 24 | Lining removes seepage recharge under β | W | Modelled; card states it; balance criterion | §2.8, §9.2 |
| 25 | Procedural and recognition justice absent; transboundary and non-stationary options cheap | W | Debrief question; `dryDrift` deck option; riparian-states preset noted for v1.2 | §1.1, §2.2 |
| 26 | One cohort cannot carry causal claims; gates depended on research results | R | Exploratory pre-registration; v1.1 and v2.0 gates rewritten | §1.4, §10.1 |
| 27 | Post-test straight after a scripted debrief measures the debrief; identical forms maximise testing effect; one item per LO has no reliability; piloting on colleagues cannot detect student floor | R | Knowledge items only pre and delayed; two parallel forms, two items per LO; piloted on previous-cohort students | §5.3, §10.2 |
| 28 | No post-survey event, no personal link across surveys, no randomisation record, no events.csv | R | `linking.code`, `treatment.assigned`, `surveys.csv`, `events.csv`, codebook | §6.2, §6.3 |
| 29 | Fixed-rule comparison arm is weak and confounds with silent mode | R | Vote vs rotating fixed rule with matched talk time | §10.3 |
| 30 | §3.3 verdict fixture wording ambiguous ("UWF highest 0.68" vs EWF 0.69) | A | Column-wise comparison stated | §2.7, §3.3 |
| 31 | §3 fixtures assume β = 1, r₀ = 0 | A | Stated; second fixture set generated on build day 3; both kept | §3 |
| 32 | The project is to be an open-source contribution; licence of code vs content undefined | A | Repository layout, dual licence (MIT / CC BY 4.0), SPDX headers with a REUSE CI job, LICENSE and LICENSE-docs, CITATION.cff and Zenodo DOI at the first tag; what is held back and until when | §7.5, §1.5, §8.2 |
| 33 | No publication plan separated the engine from the learning claims | A | JOSS paper on the engine at the v1.1 tag (a peer-reviewed code audit); serious-game paper to Simulation & Gaming or HESS after two cohorts | §7.5, §1.4, §8.4 |

Not adopted, with reasons: a single 90-minute session (reviewers' arithmetic was right; the author's constraint has been relaxed to 120); discouraging pumping by raising its cost (the dilemma is the lesson); climate-scaled demand in v1.0 (every fixture would change before the engine exists); Supabase as the room-mode backbone (no authoritative sequencer without rebuilding one).
