<!--
SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
SPDX-License-Identifier: CC-BY-4.0
-->
# Privacy leakage with the shipped aquifer capacity (ADR 0006)

Output of `python analysis/privacy_leakage.py --capacity`: the ADR 0004 measurement repeated with B_max = B₀ = 20 Mm³
(registry `basin.aquifer.capacity`). Same seed, seasons and grid as `privacy_leakage_results.md`, so the rows compare
directly. The implemented display is row I.

### Normal stock (B_low to B₀)

| In-play display | Outsider: pumping identified | Outsider: knows whether pumped | Insider: identified | Insider: knows whether pumped |
|---|---|---|---|---|
| A. §6.2 as written: exact actual-use dials, exact tank, ΣP | 100 % (100–100) | 100 % (100–100) | 100 % (100–100) | 100 % (100–100) |
| B. ΣP + exact tank (dials on allocation only) | 23 % (21–26) | 43 % (40–46) | 78 % (76–80) | 83 % (81–85) |
| C. ΣP + tank to 1 Mm³ | 9 % (8–11) | 13 % (11–15) | 39 % (37–42) | 62 % (59–65) |
| D. ΣP + tank to 2 Mm³ | 9 % (7–11) | 12 % (10–14) | 39 % (36–42) | 60 % (57–62) |
| E. ΣP only (no tank) | 9 % (7–10) | 10 % (9–12) | 38 % (35–40) | 57 % (54–59) |
| F. ΣP + actual-use band words (no tank) | 16 % (14–18) | 35 % (33–38) | 47 % (45–50) | 81 % (79–83) |
| G. ΣP + tank to 1 Mm³ + actual-use band words | 16 % (14–19) | 37 % (34–40) | 49 % (46–52) | 82 % (79–84) |
| H. ΣP + exact tank + actual-use band words | 36 % (33–39) | 60 % (57–62) | 81 % (78–83) | 92 % (90–93) |
| I. ΣP + tank to 1 Mm³ + sustainability band only | 9 % (8–11) | 17 % (15–19) | 41 % (38–43) | 66 % (63–68) |
| J. ΣP + tank to 1 Mm³ + equity bands only | 14 % (12–16) | 28 % (26–31) | 45 % (43–48) | 77 % (75–80) |
| K. ΣP + tank to 1 Mm³ + efficiency band only | 10 % (9–12) | 21 % (19–24) | 41 % (38–44) | 69 % (66–72) |

400 seasons × 3 schemes; 95 % Wilson intervals; grid 0.1 Mm³ (0..2.0); identified = all consistent candidates within 0.1 Mm³; insider = another player who knows their own pumping.

### Low stock (B_res to B_res + 2·cap); this fast path does not apply rationing — see --implemented

| In-play display | Outsider: pumping identified | Outsider: knows whether pumped | Insider: identified | Insider: knows whether pumped |
|---|---|---|---|---|
| A. §6.2 as written: exact actual-use dials, exact tank, ΣP | 100 % (100–100) | 100 % (100–100) | 100 % (100–100) | 100 % (100–100) |
| B. ΣP + exact tank (dials on allocation only) | 37 % (34–40) | 65 % (62–68) | 100 % (100–100) | 100 % (100–100) |
| C. ΣP + tank to 1 Mm³ | 10 % (9–12) | 17 % (15–19) | 40 % (38–43) | 66 % (63–69) |
| D. ΣP + tank to 2 Mm³ | 9 % (8–11) | 14 % (12–16) | 39 % (36–42) | 62 % (59–65) |
| E. ΣP only (no tank) | 9 % (7–10) | 10 % (9–12) | 38 % (35–40) | 57 % (54–59) |
| F. ΣP + actual-use band words (no tank) | 16 % (14–18) | 35 % (33–38) | 47 % (45–50) | 81 % (79–83) |
| G. ΣP + tank to 1 Mm³ + actual-use band words | 18 % (16–20) | 40 % (37–43) | 50 % (47–53) | 82 % (80–84) |
| H. ΣP + exact tank + actual-use band words | 51 % (48–54) | 78 % (75–80) | 100 % (100–100) | 100 % (100–100) |
| I. ΣP + tank to 1 Mm³ + sustainability band only | 11 % (9–13) | 20 % (18–22) | 41 % (39–44) | 69 % (66–71) |
| J. ΣP + tank to 1 Mm³ + equity bands only | 15 % (13–17) | 33 % (30–36) | 46 % (43–49) | 78 % (76–81) |
| K. ΣP + tank to 1 Mm³ + efficiency band only | 12 % (10–14) | 24 % (22–27) | 42 % (39–45) | 72 % (69–74) |

400 seasons × 3 schemes; 95 % Wilson intervals; grid 0.1 Mm³ (0..2.0); identified = all consistent candidates within 0.1 Mm³; insider = another player who knows their own pumping.
