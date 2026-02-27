/**
 * @file tests/setup.ts
 * @brief Global test setup for Vitest.
 *
 * Configures the happy-dom environment, provides global mocks for
 * Nuxt auto-imports and Vue composables used across all test files.
 */

import { vi } from 'vitest'
import { config } from '@vue/test-utils'

/* Provide global $t mock for i18n in component tests */
config.global.mocks = {
  $t: (key: string) => key,
}

/* Provide Nuxt auto-import stubs globally */
;(globalThis as Record<string, unknown>).definePageMeta = (_meta: Record<string, unknown>) => { /* no-op */ }

/* Stub localStorage for happy-dom environments that don't fully implement it */
if (typeof globalThis.localStorage === 'undefined') {
  const store: Record<string, string> = {}
  globalThis.localStorage = {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { Object.keys(store).forEach(k => delete store[k]) },
    get length() { return Object.keys(store).length },
    key: (index: number) => Object.keys(store)[index] ?? null,
  }
}

/* Provide a minimal matchMedia stub */
if (typeof globalThis.matchMedia === 'undefined') {
  globalThis.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}
