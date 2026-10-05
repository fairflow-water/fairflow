// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
//
// @fairflow/engine — pure allocation, production, indicator and welfare engine.
// Nothing but this package computes a number. See docs/blueprint.md §7.2.
// Built so far: every classical lens of §2.3, production, indicators, aquifer, welfare, verdict and resolveSeason
// (no actions, modules or events yet). The record, applyEvent and projections are the week-2 build.

export * from './types.js';
export * from './allocate.js';
export * from './production.js';
export * from './indicators.js';
export * from './aquifer.js';
export * from './welfare.js';
export * from './verdict.js';
export * from './resolveSeason.js';
