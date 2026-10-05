# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""fairflow_engine — the authoritative implementation of blueprint §2. Every function cites its section; no parameter
has a default in code (values come from a scenario or the sourced parameter registry)."""

from .allocate import FLOOR_RULES, Allocation, allocate, cel, max_value, sufficientarian, talmud, weighted_cea, weights_for
from .aquifer import inflow_loss_next, next_stock, pump_cost_per_mm3, ration_pumps, return_flow
from .indicators import (collective_score, efficiency, equity_pj, equity_se, gini, gini_corrected, one_minus_cv,
                         sustainability, triangle)
from .model import Aquifer, Basin, LensId, LensParams, MissingParameter, Pump, Scheme, Scoring, round6
from .production import value_of, yield_of
from .season import resolve_season, verdict
from .welfare import welfare
