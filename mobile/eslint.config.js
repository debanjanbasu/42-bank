// @ts-check
import { defineConfig } from 'eslint/config';
import js from '@eslint/js';
import typescriptESLint from 'typescript-eslint';

export default defineConfig(
  js.configs.recommended,
  typescriptESLint.configs.recommended,
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: typescriptESLint.parser,
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
  {
    ignores: ['node_modules/', 'dist/', '.expo/'],
  }
);