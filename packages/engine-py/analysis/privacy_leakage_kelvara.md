<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Privacy leakage on the Kelvara basin (ADR 0004 feasibility audit, re-run 2026-10-12)

Output of `uv run python analysis/privacy_leakage.py --grid`, which replaces the old-basin measurements in
`privacy_leakage_results.md`, `privacy_leakage_rationing.md` and `privacy_leakage_capacity.md`. Those files used the
v1 basin with a flat 2 Mm³ cap and counted the three farms of a season as independent draws.

## What changed in the method

- **Basin.** The shipped scenario (`default-basin.json`, loaded with `load_scenario` and the registry), resolved by the
  engine's `resolve_season`. This includes capacity as a share of demand (A 3.125, B 4.5 and C 1.7 Mm³), dry paddy
  wells (B) at an observed level of 15 Mm³ or below, lift-energy pump costs, baseflow loss and the ADR 0009 natural
  gain.
- **What the table sees.** Compared on `record.PUBLIC_RESULT_FIELDS`, which now carries the observed total
  (`pumpsTotalObserved`, to the 1 Mm³ tank resolution) instead of the exact total.
- **Action space.** The pump levels the private turn offers: whole tokens 0..⌊cap⌋ and the fractional cap. The
  0.1 Mm³ grid is kept as a sensitivity run.
- **Insiders.** An insider also sees its own `self` payload.
- **Stock.** Drawn in two regimes: B_low..B₀ (15–20 Mm³) and B_res..B_low (10–15 Mm³).
- **Statistics.** The season is the sampling unit, and the intervals reflect that:
  - per farm: Wilson interval, n = seasons;
  - pooled: cluster bootstrap over seasons, 10,000 resamples;
  - season level: "any farm identified";
  - comparison with the floor: paired cluster-bootstrap difference.
- **Structural zeros.** Rows marked "pumpable farms only" drop farms whose wells are dry. The table already knows a dry
  well delivers nothing.
- **Conservative observer.** Both observers know the stock at the start of the season exactly; the table actually sees
  only its 1 Mm³ level. This is an upper bound on what a table can infer within one season.

## Release gate (ADR 0004 item 5, as restated 2026-10-12)

On the private-turn levels, at 1,000 seasons per regime, over pumpable farms, the upper 95 % bound of the paired
difference implemented − floor must be:
- at most **5 points** for "identified" (a maintainer convention, still to be confirmed);
- at most **12 points** for "knows whether pumped".

The floor is the observed total alone.

## Results in brief (pumpable farms, private-turn levels, 1,000 seasons per regime)

| Stock | Display | Outsider identified | Outsider knows whether pumped | Insider identified | Insider knows whether pumped |
|---|---|---|---|---|---|
| 15–20 Mm³ | implemented (observed total) | 26.3 | 41.6 | 66.2 | 84.8 |
| 15–20 Mm³ | floor (observed total only) | 19.9 | 30.0 | 54.4 | 77.2 |
| 15–20 Mm³ | previous display (exact total) | 46.2 | 58.5 | 82.1 | 91.3 |
| 15–20 Mm³ | previous floor (exact total only) | 41.0 | 50.0 | 77.8 | 89.2 |
| 10–15 Mm³ | implemented (observed total) | 35.9 | 47.8 | 84.2 | 94.1 |
| 10–15 Mm³ | floor (observed total only) | 31.6 | 40.9 | 83.6 | 93.8 |
| 10–15 Mm³ | previous display (exact total) | 50.9 | 62.2 | 92.0 | 100.0 |
| 10–15 Mm³ | previous floor (exact total only) | 49.0 | 60.0 | 92.0 | 100.0 |

The figures are percentages; the intervals are in the full tables below.

- **Showing the total at the tank resolution reduces leakage in every cell.** At 15–20 Mm³ the outsider
  identifies a pumpable farm in 26 % of farm-seasons, against 46 % with the exact total. With the exact total, the
  total's fractional part told the table which farms had pumped their full fractional capacity: 3.125, 4.5 and
  1.7 Mm³ give eight distinct fractional parts.
- **The rest of the display now adds more relative to the floor than before.** The floor is coarser, but the
  observed tank level after the season is a second, differently rounded reading of the same water balance. Since the
  observer here knows the starting stock exactly, the two readings together narrow the total.
- **Gate verdicts** (upper 95 % bound of implemented − floor, in points):

  | Stock | Outsider identified (≤ 5) | Outsider knows whether pumped (≤ 12) | Insider identified (≤ 5) | Insider knows whether pumped (≤ 12) |
  |---|---|---|---|---|
  | 15–20 Mm³ | +7.8 **FAIL** | +13.3 **FAIL** | +13.4 **FAIL** | +8.6 PASS |
  | 10–15 Mm³ | +5.6 **FAIL** | +8.2 PASS | +1.0 PASS | +0.5 PASS |

  The current display does not pass the restated gate. The failures come from the conservative observer: someone who
  knows the starting stock exactly. A table sees only its 1 Mm³ level, and this script does not measure that case.
- **Grid sensitivity (0.1 Mm³ steps, 300 seasons per regime, not gated).** When farms can choose any amount, almost
  nothing is identified by an outsider: 1.7 % at 15–20 Mm³ and 4.0 % at 10–15 Mm³, against a floor of 0.0 %. The
  leakage in the tables above therefore comes mostly from the small number of pump levels the private turn offers
  (5, 6 and 3 levels).

## Two pumpers when the paddy wells are dry

At an observed level of 15 Mm³ or below, the paddy smallholders' wells (farm B) deliver nothing (ADR 0008). The
table knows this from the tank, so only two farms can pump. This held in 193 of the 1,000 seasons at 15–20 Mm³ (an
observed level of exactly 15) and in every season at 10–15 Mm³. With two pumpers, each of them knows its own pumping
and sees the total, so it knows the other's pumping up to the total's resolution:

- **Insider identified:** 84 % of pumpable farm-seasons (floor 84 %).
- **Insider knows whether the other pumped:** 94 % (floor 94 %). It was 100 % with the exact total.
- **Farm B:** known to have pumped nothing in every such season.

This exposure is the dilemma's own mechanism, not a display choice. It breaks the usual statistical-disclosure
minimum of three contributors per published total (Hundepool et al. 2025, *Handbook on Statistical Disclosure Control*,
2nd ed., §4.2.1). Unless the maintainer decides otherwise, R17's promise should say plainly that once the paddy wells
are dry, the two remaining pumpers can read each other's pumping from the total.

## Caveats

- **Pumping prior.** Each farm pumps with probability 0.6, uniformly over its levels. This is the earlier
  analysis's prior, not observed behaviour. Real tables put more weight on 0 and on full capacity.
- **One season at a time.** Each season is assessed on its own. A table that tracks the tank over several seasons
  learns more about the stock than its current level shows. It still learns less than the exact stock this script
  assumes.
- **Actions not modelled.** Expand and Orchard change capacities, and the next season's public scheme state shows
  them. The private-turn preview when rationing binds (review E11) is not modelled either.

## Full output

### Private-turn levels, stock B_low to B₀ (15–20 Mm³) — release gate

1000 seasons; pumping rationed in 34; farm B unable to pump (dry wells) in 193.

**all farms**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 31.0 (28.4–33.6) | 27.6 (24.9–30.5) / 38.9 (35.9–42.0) / 26.6 (24.0–29.4) | 42.5 (39.5–45.6) |
| implemented | outsider knows whether pumped | 45.4 (42.8–48.0) | 50.2 (47.1–53.3) / 56.4 (53.3–59.4) / 29.6 (26.9–32.5) | 65.0 (62.0–67.9) |
| implemented | insider identified | 68.4 (66.2–70.5) | 61.8 (58.7–64.8) / 69.2 (66.3–72.0) / 74.1 (71.3–76.7) | 83.0 (80.5–85.2) |
| implemented | insider knows whether pumped | 85.7 (84.3–87.1) | 87.2 (85.0–89.1) / 90.4 (88.4–92.1) / 79.6 (77.0–82.0) | 98.6 (97.7–99.2) |
| floor | outsider identified | 25.0 (22.5–27.5) | 20.5 (18.1–23.1) / 33.0 (30.2–36.0) / 21.6 (19.2–24.3) | 33.0 (30.2–36.0) |
| floor | outsider knows whether pumped | 34.5 (31.9–37.1) | 33.2 (30.4–36.2) / 46.8 (43.7–49.9) / 23.4 (20.9–26.1) | 46.8 (43.7–49.9) |
| floor | insider identified | 57.4 (55.0–59.7) | 52.8 (49.7–55.9) / 57.2 (54.1–60.2) / 62.1 (59.1–65.1) | 72.2 (69.3–74.9) |
| floor | insider knows whether pumped | 78.7 (77.1–80.3) | 80.3 (77.7–82.6) / 86.6 (84.3–88.6) / 69.2 (66.3–72.0) | 97.6 (96.5–98.4) |
| previous (exact total) | outsider identified | 49.6 (46.8–52.4) | 47.1 (44.0–50.2) / 52.9 (49.8–56.0) / 48.9 (45.8–52.0) | 64.8 (61.8–67.7) |
| previous (exact total) | outsider knows whether pumped | 61.2 (58.6–63.6) | 62.9 (59.9–65.8) / 70.8 (67.9–73.5) / 49.8 (46.7–52.9) | 79.2 (76.6–81.6) |
| previous (exact total) | insider identified | 83.3 (81.4–85.1) | 81.9 (79.4–84.2) / 81.6 (79.1–83.9) / 86.3 (84.0–88.3) | 91.3 (89.4–92.9) |
| previous (exact total) | insider knows whether pumped | 91.9 (90.8–92.9) | 94.0 (92.4–95.3) / 95.3 (93.8–96.4) / 86.3 (84.0–88.3) | 99.8 (99.3–99.9) |
| previous floor (exact total) | outsider identified | 44.8 (42.0–47.6) | 40.7 (37.7–43.8) / 47.6 (44.5–50.7) / 46.1 (43.0–49.2) | 58.9 (55.8–61.9) |
| previous floor (exact total) | outsider knows whether pumped | 53.2 (50.5–55.9) | 52.2 (49.1–55.3) / 60.5 (57.4–63.5) / 46.9 (43.8–50.0) | 68.1 (65.1–70.9) |
| previous floor (exact total) | insider identified | 79.3 (77.2–81.2) | 78.4 (75.7–80.8) / 76.7 (74.0–79.2) / 82.7 (80.2–84.9) | 88.2 (86.1–90.1) |
| previous floor (exact total) | insider knows whether pumped | 89.9 (88.7–91.1) | 92.6 (90.8–94.1) / 94.3 (92.7–95.6) / 82.7 (80.2–84.9) | 99.7 (99.1–99.9) |

**pumpable farms only (dry wells dropped)**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 26.3 (23.7–28.9) | 27.6 (24.9–30.5) / 24.3 (21.5–27.4) / 26.6 (24.0–29.4) | 32.4 (29.6–35.4) |
| implemented | outsider knows whether pumped | 41.6 (39.0–44.2) | 50.2 (47.1–53.3) / 46.0 (42.6–49.4) / 29.6 (26.9–32.5) | 60.1 (57.0–63.1) |
| implemented | insider identified | 66.2 (63.9–68.4) | 61.8 (58.7–64.8) / 61.8 (58.4–65.1) / 74.1 (71.3–76.7) | 83.0 (80.5–85.2) |
| implemented | insider knows whether pumped | 84.8 (83.3–86.2) | 87.2 (85.0–89.1) / 88.1 (85.7–90.2) / 79.6 (77.0–82.0) | 98.6 (97.7–99.2) |
| floor | outsider identified | 19.9 (17.4–22.3) | 20.5 (18.1–23.1) / 17.0 (14.5–19.7) / 21.6 (19.2–24.3) | 21.6 (19.2–24.3) |
| floor | outsider knows whether pumped | 30.0 (27.4–32.5) | 33.2 (30.4–36.2) / 34.1 (30.9–37.4) / 23.4 (20.9–26.1) | 40.4 (37.4–43.5) |
| floor | insider identified | 54.4 (52.0–56.8) | 52.8 (49.7–55.9) / 47.0 (43.5–50.4) / 62.1 (59.1–65.1) | 72.2 (69.3–74.9) |
| floor | insider knows whether pumped | 77.2 (75.6–78.8) | 80.3 (77.7–82.6) / 83.4 (80.7–85.8) / 69.2 (66.3–72.0) | 97.6 (96.5–98.4) |
| previous (exact total) | outsider identified | 46.2 (43.3–49.0) | 47.1 (44.0–50.2) / 41.6 (38.3–45.1) / 48.9 (45.8–52.0) | 57.9 (54.8–60.9) |
| previous (exact total) | outsider knows whether pumped | 58.5 (55.8–61.1) | 62.9 (59.9–65.8) / 63.8 (60.4–67.1) / 49.8 (46.7–52.9) | 76.1 (73.4–78.6) |
| previous (exact total) | insider identified | 82.1 (80.2–84.0) | 81.9 (79.4–84.2) / 77.2 (74.2–80.0) / 86.3 (84.0–88.3) | 91.3 (89.4–92.9) |
| previous (exact total) | insider knows whether pumped | 91.3 (90.2–92.4) | 94.0 (92.4–95.3) / 94.2 (92.3–95.6) / 86.3 (84.0–88.3) | 99.8 (99.3–99.9) |
| previous floor (exact total) | outsider identified | 41.0 (38.1–43.8) | 40.7 (37.7–43.8) / 35.1 (31.9–38.4) / 46.1 (43.0–49.2) | 51.5 (48.4–54.6) |
| previous floor (exact total) | outsider knows whether pumped | 50.0 (47.2–52.8) | 52.2 (49.1–55.3) / 51.1 (47.6–54.5) / 46.9 (43.8–50.0) | 65.0 (62.0–67.9) |
| previous floor (exact total) | insider identified | 77.8 (75.7–79.9) | 78.4 (75.7–80.8) / 71.1 (67.9–74.1) / 82.7 (80.2–84.9) | 88.2 (86.1–90.1) |
| previous floor (exact total) | insider knows whether pumped | 89.2 (87.9–90.4) | 92.6 (90.8–94.1) / 92.9 (91.0–94.5) / 82.7 (80.2–84.9) | 99.7 (99.1–99.9) |

**Paired difference, display − its floor, pumpable farms (cluster bootstrap 95 %)**

| Display vs floor | Measure | Difference, points | Upper 95 % | Gate margin | Verdict |
|---|---|---|---|---|---|
| implemented vs floor | outsider identified | +6.4 (+5.2 to +7.8) | +7.8 | ≤ 5 | FAIL |
| implemented vs floor | outsider knows whether pumped | +11.7 (+10.2 to +13.3) | +13.3 | ≤ 12 | FAIL |
| implemented vs floor | insider identified | +11.8 (+10.1 to +13.4) | +13.4 | ≤ 5 | FAIL |
| implemented vs floor | insider knows whether pumped | +7.5 (+6.5 to +8.6) | +8.6 | ≤ 12 | PASS |
| previous (exact total) vs previous floor (exact total) | outsider identified | +5.2 (+4.0 to +6.4) | +6.4 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | outsider knows whether pumped | +8.5 (+7.2 to +9.9) | +9.9 | ≤ 12 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider identified | +4.3 (+3.3 to +5.3) | +5.3 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider knows whether pumped | +2.1 (+1.6 to +2.8) | +2.8 | ≤ 12 | (reference) |

### Private-turn levels, stock B_res to B_low (10–15 Mm³) — release gate

1000 seasons; pumping rationed in 297; farm B unable to pump (dry wells) in 1000.

**all farms**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 57.3 (55.4–59.3) | 35.4 (32.5–38.4) / 100.0 (99.6–100.0) / 36.5 (33.6–39.5) | 100.0 (99.6–100.0) |
| implemented | outsider knows whether pumped | 65.2 (63.3–67.1) | 54.1 (51.0–57.2) / 100.0 (99.6–100.0) / 41.4 (38.4–44.5) | 100.0 (99.6–100.0) |
| implemented | insider identified | 89.5 (88.4–90.6) | 77.6 (74.9–80.1) / 100.0 (99.6–100.0) / 90.9 (89.0–92.5) | 100.0 (99.6–100.0) |
| implemented | insider knows whether pumped | 96.1 (95.2–96.9) | 93.5 (91.8–94.9) / 100.0 (99.6–100.0) / 94.7 (93.1–95.9) | 100.0 (99.6–100.0) |
| floor | outsider identified | 54.4 (52.5–56.3) | 31.4 (28.6–34.3) / 100.0 (99.6–100.0) / 31.8 (29.0–34.8) | 100.0 (99.6–100.0) |
| floor | outsider knows whether pumped | 60.6 (58.7–62.5) | 46.4 (43.3–49.5) / 100.0 (99.6–100.0) / 35.4 (32.5–38.4) | 100.0 (99.6–100.0) |
| floor | insider identified | 89.1 (87.9–90.2) | 76.4 (73.7–78.9) / 100.0 (99.6–100.0) / 90.8 (88.8–92.4) | 100.0 (99.6–100.0) |
| floor | insider knows whether pumped | 95.9 (95.0–96.8) | 93.0 (91.2–94.4) / 100.0 (99.6–100.0) / 94.7 (93.1–95.9) | 100.0 (99.6–100.0) |
| previous (exact total) | outsider identified | 67.3 (65.2–69.3) | 50.6 (47.5–53.7) / 100.0 (99.6–100.0) / 51.3 (48.2–54.4) | 100.0 (99.6–100.0) |
| previous (exact total) | outsider knows whether pumped | 74.8 (73.0–76.6) | 70.9 (68.0–73.6) / 100.0 (99.6–100.0) / 53.5 (50.4–56.6) | 100.0 (99.6–100.0) |
| previous (exact total) | insider identified | 94.7 (93.9–95.4) | 87.5 (85.3–89.4) / 100.0 (99.6–100.0) / 96.6 (95.3–97.6) | 100.0 (99.6–100.0) |
| previous (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (99.6–100.0) / 100.0 (99.6–100.0) / 100.0 (99.6–100.0) | 100.0 (99.6–100.0) |
| previous floor (exact total) | outsider identified | 66.0 (64.0–68.0) | 48.8 (45.7–51.9) / 100.0 (99.6–100.0) / 49.2 (46.1–52.3) | 100.0 (99.6–100.0) |
| previous floor (exact total) | outsider knows whether pumped | 73.3 (71.5–75.2) | 68.7 (65.8–71.5) / 100.0 (99.6–100.0) / 51.3 (48.2–54.4) | 100.0 (99.6–100.0) |
| previous floor (exact total) | insider identified | 94.7 (93.9–95.4) | 87.5 (85.3–89.4) / 100.0 (99.6–100.0) / 96.6 (95.3–97.6) | 100.0 (99.6–100.0) |
| previous floor (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (99.6–100.0) / 100.0 (99.6–100.0) / 100.0 (99.6–100.0) | 100.0 (99.6–100.0) |

**pumpable farms only (dry wells dropped)**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 35.9 (33.1–38.9) | 35.4 (32.5–38.4) / — / 36.5 (33.6–39.5) | 36.7 (33.8–39.7) |
| implemented | outsider knows whether pumped | 47.8 (44.9–50.6) | 54.1 (51.0–57.2) / — / 41.4 (38.4–44.5) | 55.7 (52.6–58.8) |
| implemented | insider identified | 84.2 (82.5–85.9) | 77.6 (74.9–80.1) / — / 90.9 (89.0–92.5) | 96.1 (94.7–97.1) |
| implemented | insider knows whether pumped | 94.1 (92.8–95.4) | 93.5 (91.8–94.9) / — / 94.7 (93.1–95.9) | 96.1 (94.7–97.1) |
| floor | outsider identified | 31.6 (28.7–34.5) | 31.4 (28.6–34.3) / — / 31.8 (29.0–34.8) | 31.8 (29.0–34.8) |
| floor | outsider knows whether pumped | 40.9 (38.0–43.8) | 46.4 (43.3–49.5) / — / 35.4 (32.5–38.4) | 46.4 (43.3–49.5) |
| floor | insider identified | 83.6 (81.9–85.3) | 76.4 (73.7–78.9) / — / 90.8 (88.8–92.4) | 96.0 (94.6–97.0) |
| floor | insider knows whether pumped | 93.8 (92.5–95.2) | 93.0 (91.2–94.4) / — / 94.7 (93.1–95.9) | 96.0 (94.6–97.0) |
| previous (exact total) | outsider identified | 50.9 (47.9–54.0) | 50.6 (47.5–53.7) / — / 51.3 (48.2–54.4) | 51.3 (48.2–54.4) |
| previous (exact total) | outsider knows whether pumped | 62.2 (59.5–64.9) | 70.9 (68.0–73.6) / — / 53.5 (50.4–56.6) | 71.0 (68.1–73.7) |
| previous (exact total) | insider identified | 92.0 (90.9–93.2) | 87.5 (85.3–89.4) / — / 96.6 (95.3–97.6) | 100.0 (99.6–100.0) |
| previous (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (99.6–100.0) / — / 100.0 (99.6–100.0) | 100.0 (99.6–100.0) |
| previous floor (exact total) | outsider identified | 49.0 (46.0–52.0) | 48.8 (45.7–51.9) / — / 49.2 (46.1–52.3) | 49.2 (46.1–52.3) |
| previous floor (exact total) | outsider knows whether pumped | 60.0 (57.3–62.7) | 68.7 (65.8–71.5) / — / 51.3 (48.2–54.4) | 68.7 (65.8–71.5) |
| previous floor (exact total) | insider identified | 92.0 (90.9–93.2) | 87.5 (85.3–89.4) / — / 96.6 (95.3–97.6) | 100.0 (99.6–100.0) |
| previous floor (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (99.6–100.0) / — / 100.0 (99.6–100.0) | 100.0 (99.6–100.0) |

**Paired difference, display − its floor, pumpable farms (cluster bootstrap 95 %)**

| Display vs floor | Measure | Difference, points | Upper 95 % | Gate margin | Verdict |
|---|---|---|---|---|---|
| implemented vs floor | outsider identified | +4.3 (+3.1 to +5.6) | +5.6 | ≤ 5 | FAIL |
| implemented vs floor | outsider knows whether pumped | +6.8 (+5.6 to +8.2) | +8.2 | ≤ 12 | PASS |
| implemented vs floor | insider identified | +0.7 (+0.4 to +1.0) | +1.0 | ≤ 5 | PASS |
| implemented vs floor | insider knows whether pumped | +0.2 (+0.1 to +0.5) | +0.5 | ≤ 12 | PASS |
| previous (exact total) vs previous floor (exact total) | outsider identified | +1.9 (+1.1 to +2.9) | +2.9 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | outsider knows whether pumped | +2.2 (+1.5 to +3.0) | +3.0 | ≤ 12 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider identified | +0.0 (+0.0 to +0.0) | +0.0 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider knows whether pumped | +0.0 (+0.0 to +0.0) | +0.0 | ≤ 12 | (reference) |

### 0.1 Mm³ grid, stock B_low to B₀ (15–20 Mm³) — sensitivity

300 seasons; pumping rationed in 6; farm B unable to pump (dry wells) in 61.

**all farms**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 8.3 (6.4–10.3) | 2.3 (1.1–4.7) / 21.0 (16.8–26.0) / 1.7 (0.7–3.8) | 21.3 (17.1–26.3) |
| implemented | outsider knows whether pumped | 16.8 (13.9–19.8) | 14.0 (10.5–18.4) / 32.7 (27.6–38.2) / 3.7 (2.1–6.4) | 34.0 (28.9–39.5) |
| implemented | insider identified | 16.3 (13.3–19.4) | 11.0 (7.9–15.0) / 27.3 (22.6–32.6) / 10.7 (7.7–14.7) | 32.0 (27.0–37.5) |
| implemented | insider knows whether pumped | 42.2 (38.3–46.1) | 47.3 (41.8–53.0) / 55.7 (50.0–61.2) / 23.7 (19.2–28.8) | 70.7 (65.3–75.5) |
| floor | outsider identified | 6.8 (5.2–8.2) | 0.0 (0.0–1.3) / 20.3 (16.2–25.2) / 0.0 (0.0–1.3) | 20.3 (16.2–25.2) |
| floor | outsider knows whether pumped | 13.8 (11.1–16.4) | 9.0 (6.3–12.8) / 30.3 (25.4–35.8) / 2.0 (0.9–4.3) | 30.3 (25.4–35.8) |
| floor | insider identified | 11.4 (9.1–13.9) | 5.0 (3.1–8.1) / 24.0 (19.5–29.1) / 5.3 (3.3–8.5) | 26.7 (22.0–31.9) |
| floor | insider knows whether pumped | 36.4 (32.8–40.2) | 39.7 (34.3–45.3) / 51.7 (46.0–57.3) / 18.0 (14.1–22.7) | 64.7 (59.1–69.9) |
| previous (exact total) | outsider identified | 16.8 (13.2–20.4) | 12.7 (9.4–16.9) / 26.3 (21.7–31.6) / 11.3 (8.2–15.4) | 27.7 (22.9–33.0) |
| previous (exact total) | outsider knows whether pumped | 32.6 (28.6–36.6) | 34.0 (28.9–39.5) / 48.0 (42.4–53.6) / 15.7 (12.0–20.2) | 56.0 (50.3–61.5) |
| previous (exact total) | insider identified | 45.9 (41.0–50.8) | 43.0 (37.5–48.7) / 46.3 (40.8–52.0) / 48.3 (42.7–54.0) | 55.0 (49.3–60.5) |
| previous (exact total) | insider knows whether pumped | 72.3 (68.8–75.7) | 76.0 (70.9–80.5) / 81.0 (76.2–85.0) / 60.0 (54.4–65.4) | 92.3 (88.8–94.8) |
| previous floor (exact total) | outsider identified | 16.2 (12.7–19.9) | 12.0 (8.8–16.2) / 25.7 (21.1–30.9) / 11.0 (7.9–15.0) | 26.7 (22.0–31.9) |
| previous floor (exact total) | outsider knows whether pumped | 26.0 (21.9–30.1) | 23.7 (19.2–28.8) / 39.7 (34.3–45.3) / 14.7 (11.1–19.1) | 40.7 (35.3–46.3) |
| previous floor (exact total) | insider identified | 45.0 (40.1–49.9) | 42.0 (36.6–47.7) / 45.7 (40.1–51.3) / 47.3 (41.8–53.0) | 54.0 (48.3–59.6) |
| previous floor (exact total) | insider knows whether pumped | 69.6 (65.9–73.1) | 73.7 (68.4–78.3) / 79.3 (74.4–83.5) / 55.7 (50.0–61.2) | 90.3 (86.5–93.2) |

**pumpable farms only (dry wells dropped)**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 1.7 (0.5–3.1) | 2.3 (1.1–4.7) / 0.8 (0.2–3.0) / 1.7 (0.7–3.8) | 2.3 (1.1–4.7) |
| implemented | outsider knows whether pumped | 10.7 (8.2–13.4) | 14.0 (10.5–18.4) / 15.5 (11.4–20.6) / 3.7 (2.1–6.4) | 21.3 (17.1–26.3) |
| implemented | insider identified | 10.3 (7.5–13.2) | 11.0 (7.9–15.0) / 8.8 (5.8–13.1) / 10.7 (7.7–14.7) | 15.7 (12.0–20.2) |
| implemented | insider knows whether pumped | 38.0 (34.2–41.9) | 47.3 (41.8–53.0) / 44.4 (38.2–50.7) / 23.7 (19.2–28.8) | 65.0 (59.4–70.2) |
| floor | outsider identified | 0.0 (0.0–0.0) | 0.0 (0.0–1.3) / 0.0 (0.0–1.6) / 0.0 (0.0–1.3) | 0.0 (0.0–1.3) |
| floor | outsider knows whether pumped | 7.5 (5.4–9.7) | 9.0 (6.3–12.8) / 12.6 (8.9–17.4) / 2.0 (0.9–4.3) | 15.7 (12.0–20.2) |
| floor | insider identified | 5.0 (3.1–7.1) | 5.0 (3.1–8.1) / 4.6 (2.6–8.1) / 5.3 (3.3–8.5) | 7.3 (4.9–10.9) |
| floor | insider knows whether pumped | 31.8 (28.2–35.6) | 39.7 (34.3–45.3) / 39.3 (33.4–45.6) / 18.0 (14.1–22.7) | 58.7 (53.0–64.1) |
| previous (exact total) | outsider identified | 10.7 (7.5–14.3) | 12.7 (9.4–16.9) / 7.5 (4.8–11.6) / 11.3 (8.2–15.4) | 13.0 (9.7–17.3) |
| previous (exact total) | outsider knows whether pumped | 27.7 (23.9–31.5) | 34.0 (28.9–39.5) / 34.7 (29.0–41.0) / 15.7 (12.0–20.2) | 50.3 (44.7–56.0) |
| previous (exact total) | insider identified | 42.0 (37.3–46.7) | 43.0 (37.5–48.7) / 32.6 (27.0–38.8) / 48.3 (42.7–54.0) | 55.0 (49.3–60.5) |
| previous (exact total) | insider knows whether pumped | 70.3 (66.7–73.8) | 76.0 (70.9–80.5) / 76.2 (70.4–81.1) / 60.0 (54.4–65.4) | 92.3 (88.8–94.8) |
| previous floor (exact total) | outsider identified | 10.1 (6.9–13.6) | 12.0 (8.8–16.2) / 6.7 (4.2–10.6) / 11.0 (7.9–15.0) | 12.0 (8.8–16.2) |
| previous floor (exact total) | outsider knows whether pumped | 20.6 (16.9–24.4) | 23.7 (19.2–28.8) / 24.3 (19.3–30.1) / 14.7 (11.1–19.1) | 34.7 (29.5–40.2) |
| previous floor (exact total) | insider identified | 41.0 (36.3–45.7) | 42.0 (36.6–47.7) / 31.8 (26.2–38.0) / 47.3 (41.8–53.0) | 54.0 (48.3–59.6) |
| previous floor (exact total) | insider knows whether pumped | 67.3 (63.7–70.9) | 73.7 (68.4–78.3) / 74.1 (68.2–79.2) / 55.7 (50.0–61.2) | 90.3 (86.5–93.2) |

**Paired difference, display − its floor, pumpable farms (cluster bootstrap 95 %)**

| Display vs floor | Measure | Difference, points | Upper 95 % | Gate margin | Verdict |
|---|---|---|---|---|---|
| implemented vs floor | outsider identified | +1.7 (+0.5 to +3.1) | +3.1 | ≤ 5 | (reference) |
| implemented vs floor | outsider knows whether pumped | +3.2 (+1.8 to +4.8) | +4.8 | ≤ 12 | (reference) |
| implemented vs floor | insider identified | +5.2 (+3.2 to +7.5) | +7.5 | ≤ 5 | (reference) |
| implemented vs floor | insider knows whether pumped | +6.2 (+4.2 to +8.3) | +8.3 | ≤ 12 | (reference) |
| previous (exact total) vs previous floor (exact total) | outsider identified | +0.6 (+0.0 to +1.5) | +1.5 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | outsider knows whether pumped | +7.0 (+5.4 to +8.8) | +8.8 | ≤ 12 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider identified | +1.0 (+0.1 to +2.0) | +2.0 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider knows whether pumped | +3.0 (+1.8 to +4.2) | +4.2 | ≤ 12 | (reference) |

### 0.1 Mm³ grid, stock B_res to B_low (10–15 Mm³) — sensitivity

300 seasons; pumping rationed in 95; farm B unable to pump (dry wells) in 300.

**all farms**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 36.0 (34.7–37.6) | 4.0 (2.3–6.9) / 100.0 (98.7–100.0) / 4.0 (2.3–6.9) | 100.0 (98.7–100.0) |
| implemented | outsider knows whether pumped | 41.9 (40.1–43.8) | 22.3 (18.0–27.4) / 100.0 (98.7–100.0) / 3.3 (1.8–6.0) | 100.0 (98.7–100.0) |
| implemented | insider identified | 58.8 (55.7–62.0) | 36.0 (30.8–41.6) / 100.0 (98.7–100.0) / 40.3 (34.9–46.0) | 100.0 (98.7–100.0) |
| implemented | insider knows whether pumped | 74.8 (71.9–77.8) | 63.7 (58.1–68.9) / 100.0 (98.7–100.0) / 60.7 (55.0–66.0) | 100.0 (98.7–100.0) |
| floor | outsider identified | 33.3 (33.3–33.3) | 0.0 (0.0–1.3) / 100.0 (98.7–100.0) / 0.0 (0.0–1.3) | 100.0 (98.7–100.0) |
| floor | outsider knows whether pumped | 37.3 (36.0–38.8) | 10.7 (7.7–14.7) / 100.0 (98.7–100.0) / 1.3 (0.5–3.4) | 100.0 (98.7–100.0) |
| floor | insider identified | 53.6 (50.7–56.7) | 28.0 (23.2–33.3) / 100.0 (98.7–100.0) / 32.7 (27.6–38.2) | 100.0 (98.7–100.0) |
| floor | insider knows whether pumped | 71.9 (68.9–74.9) | 59.0 (53.4–64.4) / 100.0 (98.7–100.0) / 56.7 (51.0–62.2) | 100.0 (98.7–100.0) |
| previous (exact total) | outsider identified | 47.3 (44.2–50.4) | 21.0 (16.8–26.0) / 100.0 (98.7–100.0) / 21.0 (16.8–26.0) | 100.0 (98.7–100.0) |
| previous (exact total) | outsider knows whether pumped | 57.2 (54.1–60.3) | 44.7 (39.1–50.3) / 100.0 (98.7–100.0) / 27.0 (22.3–32.3) | 100.0 (98.7–100.0) |
| previous (exact total) | insider identified | 95.6 (94.2–96.8) | 90.7 (86.8–93.5) / 100.0 (98.7–100.0) / 96.0 (93.1–97.7) | 100.0 (98.7–100.0) |
| previous (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (98.7–100.0) / 100.0 (98.7–100.0) / 100.0 (98.7–100.0) | 100.0 (98.7–100.0) |
| previous floor (exact total) | outsider identified | 47.1 (44.0–50.2) | 20.7 (16.5–25.6) / 100.0 (98.7–100.0) / 20.7 (16.5–25.6) | 100.0 (98.7–100.0) |
| previous floor (exact total) | outsider knows whether pumped | 54.9 (51.9–58.0) | 42.0 (36.6–47.7) / 100.0 (98.7–100.0) / 22.7 (18.3–27.7) | 100.0 (98.7–100.0) |
| previous floor (exact total) | insider identified | 95.6 (94.2–96.8) | 90.7 (86.8–93.5) / 100.0 (98.7–100.0) / 96.0 (93.1–97.7) | 100.0 (98.7–100.0) |
| previous floor (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (98.7–100.0) / 100.0 (98.7–100.0) / 100.0 (98.7–100.0) | 100.0 (98.7–100.0) |

**pumpable farms only (dry wells dropped)**

| Display | Measure | Pooled % (cluster bootstrap 95 %) | Per farm A/B/C % (Wilson, n = seasons) | Any farm, season level % (Wilson) |
|---|---|---|---|---|
| implemented | outsider identified | 4.0 (2.0–6.3) | 4.0 (2.3–6.9) / — / 4.0 (2.3–6.9) | 4.0 (2.3–6.9) |
| implemented | outsider knows whether pumped | 12.8 (10.2–15.7) | 22.3 (18.0–27.4) / — / 3.3 (1.8–6.0) | 23.3 (18.9–28.4) |
| implemented | insider identified | 38.2 (33.5–43.0) | 36.0 (30.8–41.6) / — / 40.3 (34.9–46.0) | 51.3 (45.7–56.9) |
| implemented | insider knows whether pumped | 62.2 (57.8–66.7) | 63.7 (58.1–68.9) / — / 60.7 (55.0–66.0) | 78.7 (73.7–82.9) |
| floor | outsider identified | 0.0 (0.0–0.0) | 0.0 (0.0–1.3) / — / 0.0 (0.0–1.3) | 0.0 (0.0–1.3) |
| floor | outsider knows whether pumped | 6.0 (4.0–8.2) | 10.7 (7.7–14.7) / — / 1.3 (0.5–3.4) | 10.7 (7.7–14.7) |
| floor | insider identified | 30.3 (26.0–35.0) | 28.0 (23.2–33.3) / — / 32.7 (27.6–38.2) | 42.0 (36.6–47.7) |
| floor | insider knows whether pumped | 57.8 (53.3–62.3) | 59.0 (53.4–64.4) / — / 56.7 (51.0–62.2) | 75.3 (70.2–79.9) |
| previous (exact total) | outsider identified | 21.0 (16.3–25.7) | 21.0 (16.8–26.0) / — / 21.0 (16.8–26.0) | 21.0 (16.8–26.0) |
| previous (exact total) | outsider knows whether pumped | 35.8 (31.2–40.5) | 44.7 (39.1–50.3) / — / 27.0 (22.3–32.3) | 47.0 (41.4–52.6) |
| previous (exact total) | insider identified | 93.3 (91.3–95.2) | 90.7 (86.8–93.5) / — / 96.0 (93.1–97.7) | 100.0 (98.7–100.0) |
| previous (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (98.7–100.0) / — / 100.0 (98.7–100.0) | 100.0 (98.7–100.0) |
| previous floor (exact total) | outsider identified | 20.7 (16.0–25.3) | 20.7 (16.5–25.6) / — / 20.7 (16.5–25.6) | 20.7 (16.5–25.6) |
| previous floor (exact total) | outsider knows whether pumped | 32.3 (27.8–37.0) | 42.0 (36.6–47.7) / — / 22.7 (18.3–27.7) | 42.0 (36.6–47.7) |
| previous floor (exact total) | insider identified | 93.3 (91.3–95.2) | 90.7 (86.8–93.5) / — / 96.0 (93.1–97.7) | 100.0 (98.7–100.0) |
| previous floor (exact total) | insider knows whether pumped | 100.0 (100.0–100.0) | 100.0 (98.7–100.0) / — / 100.0 (98.7–100.0) | 100.0 (98.7–100.0) |

**Paired difference, display − its floor, pumpable farms (cluster bootstrap 95 %)**

| Display vs floor | Measure | Difference, points | Upper 95 % | Gate margin | Verdict |
|---|---|---|---|---|---|
| implemented vs floor | outsider identified | +4.0 (+2.0 to +6.3) | +6.3 | ≤ 5 | (reference) |
| implemented vs floor | outsider knows whether pumped | +6.8 (+4.8 to +9.0) | +9.0 | ≤ 12 | (reference) |
| implemented vs floor | insider identified | +7.8 (+5.2 to +10.7) | +10.7 | ≤ 5 | (reference) |
| implemented vs floor | insider knows whether pumped | +4.3 (+2.7 to +6.2) | +6.2 | ≤ 12 | (reference) |
| previous (exact total) vs previous floor (exact total) | outsider identified | +0.3 (+0.0 to +1.0) | +1.0 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | outsider knows whether pumped | +3.5 (+2.0 to +5.2) | +5.2 | ≤ 12 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider identified | +0.0 (+0.0 to +0.0) | +0.0 | ≤ 5 | (reference) |
| previous (exact total) vs previous floor (exact total) | insider knows whether pumped | +0.0 (+0.0 to +0.0) | +0.0 | ≤ 12 | (reference) |

Seed 20261012; a farm pumps with probability 0.6, uniformly over its levels; identified = all consistent candidates within 0.1 Mm³; 10000 cluster-bootstrap resamples over seasons; gate margins 5 points (identified, maintainer convention to confirm) and 12 points (knows whether pumped).
