// SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
// SPDX-License-Identifier: MIT
//
// typescript-eslint `recommendedTypeChecked` on the engine sources (type-aware rules); tests get the
// non-type-checked set, since they are excluded from the build tsconfig.
import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist/**', 'coverage/**', 'eslint.config.js', 'vitest.config.ts'] },
  js.configs.recommended,
  {
    files: ['src/**/*.ts'],
    ignores: ['src/**/*.test.ts', 'src/**/*.testutil.ts'],
    extends: [tseslint.configs.recommendedTypeChecked],
    languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } },
  },
  {
    files: ['src/**/*.test.ts', 'src/**/*.testutil.ts'],
    extends: [tseslint.configs.recommended],
  },
);
