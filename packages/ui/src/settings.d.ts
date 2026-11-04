// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
// SPDX-License-Identifier: MIT
//
// Set at build time by vite.config.ts from the shipped scenario (ADR 0018): the default hand-over season and the
// longest game, for the start page's hand-over choice. Nothing else from the scenario is bundled.
declare const __ROOM_SETTINGS__: { authorityHandoverSeason: number; longestGame: number };
