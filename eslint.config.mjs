import js from '@eslint/js'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: [
      '**/.venv/**',
      '**/dist/**',
      '**/coverage/**',
      '_site/**',
      'output/**',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['scripts/**/*.mjs'],
    languageOptions: {
      globals: {
        URL: 'readonly',
        console: 'readonly',
      },
    },
  },
  {
    files: ['**/*.{ts,tsx,mts}'],
    languageOptions: {
      globals: {
        Blob: 'readonly',
        Deno: 'readonly',
        File: 'readonly',
        IDBKeyRange: 'readonly',
        URL: 'readonly',
        console: 'readonly',
        crypto: 'readonly',
        document: 'readonly',
        indexedDB: 'readonly',
        navigator: 'readonly',
        process: 'readonly',
        structuredClone: 'readonly',
        window: 'readonly',
      },
    },
  },
)
