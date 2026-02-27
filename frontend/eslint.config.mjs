/**
 * @file eslint.config.mjs
 * @brief ESLint flat configuration for the Nexara frontend.
 *
 * Imports the auto-generated Nuxt-aware config from the .nuxt build
 * directory and allows project-level rule overrides.
 */

// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    files: ['tests/**/*.ts'],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
)
