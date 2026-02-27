/**
 * @file tailwind.config.ts
 * @brief Tailwind CSS configuration with Flowbite plugin and custom theme tokens.
 *
 * Uses the `class` strategy for dark mode to support manual toggle via
 * the useDarkMode composable. Extends the default theme with CSS custom
 * properties that are overridden at runtime by the branding API.
 */

import type { Config } from 'tailwindcss'
import flowbite from 'flowbite/plugin'
import typography from '@tailwindcss/typography'

export default <Config>{
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.{js,ts}',
    './plugins/**/*.{js,ts}',
    './app.vue',
    './node_modules/flowbite-vue/**/*.{js,ts,vue}',
    './node_modules/flowbite/**/*.{js,ts}',
  ],

  darkMode: 'class',

  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: 'var(--color-primary, #3b82f6)',
          600: 'var(--color-primary-dark, #2563eb)',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        accent: {
          500: 'var(--color-accent, #8b5cf6)',
        },
        surface: {
          light: 'var(--color-surface-light, #ffffff)',
          dark: 'var(--color-surface-dark, #1f2937)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        base: 'var(--radius-base, 0.5rem)',
      },
    },
  },

  plugins: [flowbite, typography],
}
