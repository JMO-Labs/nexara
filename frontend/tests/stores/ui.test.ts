/**
 * @file tests/stores/ui.test.ts
 * @brief TDD tests for the UI Pinia store.
 *
 * Tests dark mode toggle, sidebar state, and toast notifications.
 * Written before the store implementation (TDD red phase).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from '~/stores/ui'

describe('ui store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('starts with default state', () => {
    const store = useUiStore()

    expect(store.darkMode).toBe(false)
    expect(store.sidebarOpen).toBe(true)
    expect(store.toasts).toEqual([])
  })

  it('toggleDarkMode() flips the dark mode flag', () => {
    const store = useUiStore()

    store.toggleDarkMode()
    expect(store.darkMode).toBe(true)

    store.toggleDarkMode()
    expect(store.darkMode).toBe(false)
  })

  it('toggleDarkMode() persists preference to localStorage', () => {
    const store = useUiStore()

    store.toggleDarkMode()
    expect(localStorage.getItem('nexara-dark-mode')).toBe('true')

    store.toggleDarkMode()
    expect(localStorage.getItem('nexara-dark-mode')).toBe('false')
  })

  it('initializes dark mode from localStorage', () => {
    localStorage.setItem('nexara-dark-mode', 'true')

    const store = useUiStore()
    store.initDarkMode()

    expect(store.darkMode).toBe(true)
  })

  it('initializes dark mode from system preference when no saved pref', () => {
    vi.spyOn(globalThis, 'matchMedia').mockReturnValue({
      matches: true,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })

    const store = useUiStore()
    store.initDarkMode()

    expect(store.darkMode).toBe(true)
  })

  it('toggleSidebar() flips the sidebar state', () => {
    const store = useUiStore()

    store.toggleSidebar()
    expect(store.sidebarOpen).toBe(false)

    store.toggleSidebar()
    expect(store.sidebarOpen).toBe(true)
  })

  it('showToast() adds a toast notification', () => {
    const store = useUiStore()

    store.showToast({ type: 'success', message: 'It worked!' })

    expect(store.toasts).toHaveLength(1)
    expect(store.toasts[0].type).toBe('success')
    expect(store.toasts[0].message).toBe('It worked!')
    expect(store.toasts[0].id).toBeDefined()
  })

  it('showToast() supports multiple toasts', () => {
    const store = useUiStore()

    store.showToast({ type: 'success', message: 'First' })
    store.showToast({ type: 'error', message: 'Second' })

    expect(store.toasts).toHaveLength(2)
  })

  it('dismissToast() removes a specific toast', () => {
    const store = useUiStore()

    store.showToast({ type: 'info', message: 'To dismiss' })
    const toastId = store.toasts[0].id

    store.dismissToast(toastId)

    expect(store.toasts).toHaveLength(0)
  })
})
