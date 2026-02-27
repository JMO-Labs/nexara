/**
 * @file composables/useDarkMode.ts
 * @brief Dark mode composable with system preference detection.
 *
 * Manages the `dark` CSS class on `<html>` for Tailwind's class-based
 * dark mode strategy. Persists the preference to localStorage and
 * detects the system's `prefers-color-scheme` on first visit.
 */

import { ref } from 'vue'

/** @brief localStorage key for dark mode preference. */
const STORAGE_KEY = 'nexara-dark-mode'

/**
 * @brief Composable for toggling and reading dark mode state.
 * @returns isDark ref and toggle function.
 */
export function useDarkMode() {
  const isDark = ref(false)

  /** Detect the initial state from storage or system preference. */
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved !== null) {
    isDark.value = saved === 'true'
  } else if (typeof window !== 'undefined' && window.matchMedia) {
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }

  applyClass(isDark.value)

  /** @brief Toggle dark mode and persist the choice. */
  function toggle(): void {
    isDark.value = !isDark.value
    localStorage.setItem(STORAGE_KEY, String(isDark.value))
    applyClass(isDark.value)
  }

  /** @brief Apply or remove the `dark` class on the root element. */
  function applyClass(dark: boolean): void {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', dark)
    }
  }

  return { isDark, toggle }
}
