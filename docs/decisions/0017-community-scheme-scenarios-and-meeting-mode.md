<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew, IHE Delft, and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# ADR 0017: Community-scheme scenarios and meeting mode

- Status: **proposed** (draft PR). The direction and the answers below come from the maintainer, 2026-10-29. Nothing is built.
- After v1.1: it depends on Modules 2 to 5 and on table mode (E3b).

## Context

Fairflow models a river basin with three irrigation schemes as the seats: the Kelvara basin (ADR 0007), with river cards and a shared aquifer (ADR 0008, ADR 0009). The maintainer wants it to handle a second kind of case as well: **a single community irrigation scheme**. Such a scheme may draw on surface water through canals, on groundwater, or on both (conjunctive use). It should also be playable by **farmers and extension workers in a meeting or brainstorming setting**, not only by students in a course. **The basin game and its logic must not be compromised.**

The first real case is Melka Chefe, a surface-water scheme with channel irrigation. The maintainer's fieldwork plan (`Melkachefe_variables_for_Fairflow.docx`, not in this repository) lists the variables to collect and how each would become a Fairflow parameter. No values have been collected yet.

Much of what a scheme needs is already in the blueprint, in modules not built for v1.0:
- §2.8 M2 Rotation: "Tail-end receives last".
- §2.8 M2 Steal: "Upstream i moves 1 Mm³ from i+1", with monitoring and fines.
- §2.8 M3 Conveyance: loss λ and lining, with the seepage recharging the aquifer.
- §2.8 M4 "outgrowers": a fourth claimant.
- §2.8 M5 River: a fifth voter who holds the reserve.

## Decision

### 1. A scenario declares three settings, and Kelvara is one combination of them

| Setting | Options | Kelvara (unchanged) |
|---|---|---|
| `layout`: what a seat is | `basin`: irrigation schemes along a river · `scheme`: units of one community scheme | `basin` |
| `source`: where the water comes from | `surface` · `groundwater` · `conjunctive` | `conjunctive` |
| `setting`: who plays, and how | `classroom` · `meeting` | `classroom` |

A scenario that leaves a setting out gets Kelvara's value. This is how the current logic stays untouched (decision 6).

### 2. The scheme layout

- **Seats** are the scheme's reaches (head, middle, tail), in canal order, plus an **expansion area**: land outside the designed command area. This is the maintainer's choice, made 2026-10-29.
  - Tenure (who holds the land and who farms it, owners and tenants) goes into the role cards and private goals, not into the seats. M6 side payments can carry rent.
  - The parcel-level data allow other groupings (WUA blocks or outlet groups, or user types) to be tested in the balance harness before a case is fixed.
- **The Authority** is the scheme manager: the WUA or the irrigation office, holding the fee income and the maintenance budget (M3).
- **M5** is **the river and downstream users**. The mechanics are the same as in §2.8, and the reserve is read as the release past the headworks.
- **Position relative to the canal matters too** (maintainer, 2026-10-29). A parcel may lie above the canal water surface, level with it, or below it, and this is collected per parcel:
  - parcels **above** the canal must lift water with a motor or by hand. The cost is the existing pumping-cost mechanic, applied to a canal lift, so gravity users and lift users of one reach face different costs for the same water;
  - parcels **below** the canal can breach or cut the bank and let water run onto their land. This is a form of M2 Steal: it takes water from the reaches below, and the repair is charged to the M3 maintenance budget.
- **Order matters physically.** Water reaches each reach after the losses upstream of it (M3 conveyance, applied reach by reach), and in dry years rotation serves the tail last (M2).
- **Recognition of the expansion area is the table's choice.** It is a vote with three options, modelled on the floor-rule vote (ADR 0003):
  - **not recognised**: no allocation. The expansion area can still take water at an off-take outside the plan (M2 Steal) or pump, where the source allows it;
  - **recognised in full**: its stated demand enters the lenses like any reach's;
  - **recognised in part**: up to a floor. The floor's size is a sourced value or a labelled convention.
- **The claim basis.** The vote sets the claim basis for the expansion area only. Reaches inside the command area keep stated demand, as in the basin. The debrief adds one flip: a replay with every reach on designed command area instead of demand.

### 3. The three source types

The basin model is already conjunctive. Each source type uses the existing mechanics with parts switched off:

- **Surface.** The river cards and the canal modules (M2, M3) apply; the aquifer and pumping are off. If the scenario says private wells or lift pumps exist as a drought backup, the pumping mechanic can be switched on for the seats that have them.
- **Groundwater.** There are no river cards. The aquifer is the shared stock, and the existing pumping dilemma (ADR 0008) becomes the core. The lenses divide what may be pumped in a season instead of river water.
- **Conjunctive.** Both apply, as in Kelvara, at scheme scale.

**Recharge, where the aquifer is on.** Two terms, either or both of which a scenario can use. This follows the maintainer's answer, "can be both":
- **Rainfall recharge by climate card.** Each card can carry a recharge volume, so a dry year recharges less. In a groundwater scheme this is how the season's luck reaches the players. Kelvara gives none, so its behaviour is unchanged.
- **Capture.** ADR 0009's gain, G(B) = min(r₀, κ·(B₀ − B_observed)), stays capture-consistent: what the aquifer gains is taken from natural discharge. With a river in the game, the river loses it next season, as now. Without one, the captured water is discharge lost to **downstream users** (springs, baseflow, wetlands). It is recorded against M5 and the sustainability dial, not created from nothing.
- Return-flow recharge (ADR 0007) and spill above full apply as now. In a groundwater scheme, spill leaves the game as discharge to downstream users.

### 4. Meeting mode, for farmers and extension workers

- **No personal phones needed.** One shared screen or projector carries the game. The facilitator enters each seat's choice, and paper cards are the fallback. This needs table mode (E3b) and the facilitator-entered path of issue #9.
- **Plain presentation:**
  - water is shown in turns, hours or cubes, in local units the scenario names;
  - lens cards use plain names and pictures (§5.3);
  - the facilitator speaks the prompts.
- **Roles from real life.** Farmers play their own reach or user type. Extension workers play the scheme manager, or swap roles.
- **"What would each rule have done?"** After each season, the table can see the same season replayed under every enabled lens. The engine already replays seasons with a lens forced (the balance harness does this), so this adds a view, not a mechanic. The maintainer chose this for meeting mode, 2026-10-29.
- **Flexible rounds.** The facilitator may shorten rounds or turn off the score display. The classroom timetable (ADR 0001) is unchanged.
- **Language.** English first; Amharic later (maintainer, 2026-10-29).
- **Research stays off.** ADR 0011's consent was written for course students. A community setting needs its own consent text and ethics approval before research mode can be enabled there, and the fieldwork plan's data-release agreement must be signed first.

### 5. Scenarios

- The default community scheme is **hypothetical**, like Kelvara: typical literature values, each with a source, or labelled conventions. Variants exist for each source type.
- **Melka Chefe** is a labelled real-case preset (`surface`, `scheme`), built only from collected, flagged values (measured, derived, literature or assumed, as the fieldwork plan specifies) once the data exist and their release is agreed in writing.

### 6. The basin game is not compromised

- Every new scenario field is optional, and its default reproduces today's behaviour exactly. `default-basin` does not change.
- A regression test is added before any engine change: Kelvara's record vectors, UI fixtures and balance results must come out unchanged.
- The §9.2 balance criteria apply to every scenario. Scheme mode adds three criteria, whose thresholds the maintainer sets:
  - **position matters:** under some lens, the tail and the expansion area get visibly less of what they were allocated, and some lens narrows that gap;
  - **recognition matters:** the expansion area's share differs across the vote's options and across lenses;
  - **steal has a price:** taking at the head pays privately, and costs the table when monitoring is on.
- The ADR 0004 privacy gate is rerun on any new display. Delivery per reach may reveal more than the basin view does.
- One engine serves both layouts. The basin is the layout with one off-take per scheme along the river. There is no second model.

### 7. Evaluation

1. **The balance harness** on the hypothetical community scheme in all three source variants, with no tuning of the table mix.
2. **Against observation, for Melka Chefe.** Does the model, run with the rules in use, reproduce the measured adequacy by reach and the measured 1 − CV of adequacy? That second quantity is the E_PJ dial's measure (Molden & Gates 1990).
3. **Meeting mode** in a pilot with WUA members and extension workers. The pilot checks:
   - the session length;
   - whether each rule is understood;
   - whether the group deliberates rather than only plays.

## Consequences

- Scenario schema 3.x gains `layout`, `source` and `setting`, recharge by card, and the recognition vote's settings. The registry gains the scheme parameters, each with a source.
- One new public event is needed for the recognition vote, and perhaps one for its result. They are to be added to §6.2 through the generated table, after acceptance.
- Build order:
  1. this ADR;
  2. M2–M5 (v1.1);
  3. the regression guard;
  4. the hypothetical community scheme in three source variants;
  5. table mode, then meeting mode;
  6. the Melka Chefe preset after fieldwork.
- **A symbol clash to settle before any scenario file uses it.** The fieldwork plan uses κ for a vulnerability weight, while κ is the aquifer coefficient in ADR 0008 and ADR 0009.

## Open questions

1. **The recognition vote's rules.** Does the expansion seat vote on its own recognition? Is the vote held once per game, or can it be reopened each season?
2. **The scheme-mode balance thresholds** (decision 6).
3. **Meeting mode's research and consent route.** Who approves it, and when?

## Sources

- Blueprint §2.5 (E_PJ), §2.8 (M2–M6), §5.3 (lens cards), §9.2 (balance criteria), R2, R8.
- ADR 0001, ADR 0003, ADR 0004, ADR 0007, ADR 0008, ADR 0009, ADR 0011.
- Molden & Gates 1990, the equity indicator behind E_PJ, as cited in blueprint §2.5.
- The maintainer's fieldwork plan for Melka Chefe (not in this repository).
