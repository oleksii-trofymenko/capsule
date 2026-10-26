// ESLint flat config (ADR-018). Formatting is Prettier's job; ESLint checks correctness.
// Dev dependencies: eslint, eslint-config-expo, typescript-eslint.
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');
const tseslint = require('typescript-eslint');

module.exports = defineConfig([
  expoConfig,
  {
    files: ['**/*.ts', '**/*.tsx'],
    extends: [tseslint.configs.strictTypeChecked],
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: __dirname },
    },
  },
  {
    rules: {
      'no-console': 'error',
    },
  },
  { ignores: ['dist/*', '.expo/*', 'ios/*', 'android/*', 'eslint.config.js'] },
]);
