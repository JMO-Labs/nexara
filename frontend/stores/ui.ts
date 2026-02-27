/**
 * @file stores/ui.ts
 * @brief Pinia store for global UI state.
 *
 * Manages dark mode preference (with localStorage persistence and
 * system preference detection), search modal state, and toast
 * notification queue.
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ToastItem } from '~/types/api'

/** @brief localStorage key for persisting dark mode preference. */
const DARK_MODE_KEY = 'nexara-dark-mode'

export const useUiStore = defineStore('ui', () => {
  /** @brief Whether dark mode is active. */
  const darkMode = ref(false)

  /** @brief Whether the search modal is open. */
  const searchOpen = ref(false)

  /** @brief Stack of active toast notifications. */
  const toasts = ref<ToastItem[]>([])

  /**
   * @brief Toggle dark mode and persist the preference.
   *
   * Also toggles the `dark` CSS class on the `<html>` element
   * for Tailwind's `dark:` variant support.
   */
  function toggleDarkMode(): void {
    darkMode.value = !darkMode.value
    localStorage.setItem(DARK_MODE_KEY, String(darkMode.value))

    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', darkMode.value)
    }
  }

  /**
   * @brief Initialize dark mode from saved preference or system setting.
   *
   * Priority: localStorage > prefers-color-scheme > default (light).
   */
  function initDarkMode(): void {
    const saved = localStorage.getItem(DARK_MODE_KEY)
    if (saved !== null) {
      darkMode.value = saved === 'true'
    } else if (typeof window !== 'undefined') {
      darkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }

    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', darkMode.value)
    }
  }

  /** @brief Open the search modal. */
  function openSearch(): void {
    searchOpen.value = true
  }

  /** @brief Close the search modal. */
  function closeSearch(): void {
    searchOpen.value = false
  }

  /**
   * @brief Show a toast notification.
   * @param options - Toast type and message.
   */
  function showToast(options: { type: ToastItem['type']; message: string; duration?: number }): void {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    toasts.value.push({
      id,
      type: options.type,
      message: options.message,
      duration: options.duration ?? 5000,
    })
  }

  /**
   * @brief Dismiss a specific toast by ID.
   * @param id - The toast ID to remove.
   */
  function dismissToast(id: string): void {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return {
    darkMode,
    searchOpen,
    toasts,
    toggleDarkMode,
    initDarkMode,
    openSearch,
    closeSearch,
    showToast,
    dismissToast,
  }
})
