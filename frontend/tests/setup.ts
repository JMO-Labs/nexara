/**
 * @file tests/setup.ts
 * @brief Global test setup for Vitest.
 *
 * Configures the happy-dom environment, provides global mocks for
 * Nuxt auto-imports and Vue composables used across all test files.
 */

import { vi } from "vitest";
import { config } from "@vue/test-utils";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key, te: () => true }),
}));

/* Stub useI18n globally for Nuxt auto-imported components */
(globalThis as Record<string, unknown>).useI18n = () => ({
  t: (key: string) => key,
  te: () => true,
});

/* Provide global $t mock for i18n in component tests */
config.global.mocks = {
  $t: (key: string) => key,
};

/* Provide Nuxt auto-import stubs globally */
(globalThis as Record<string, unknown>).definePageMeta = (
  _meta: Record<string, unknown>,
) => {
  /* no-op */
};
(globalThis as Record<string, unknown>).defineNuxtRouteMiddleware = (
  fn: (...args: unknown[]) => unknown,
) => fn;
(globalThis as Record<string, unknown>).navigateTo = (
  to: unknown,
  _opts?: unknown,
) => to;
(globalThis as Record<string, unknown>).useRoute = () => ({
  path: "/",
  params: {},
  query: {},
  fullPath: "/",
});
(globalThis as Record<string, unknown>).useRouter = () => ({
  push: vi.fn(),
  replace: vi.fn(),
});

/*
 * Always replace localStorage with a complete in-memory implementation.
 * happy-dom provides a partial localStorage that omits clear() when no
 * --localstorage-file path is configured, causing tests to fail.
 */
const _localStore: Record<string, string> = {};
Object.defineProperty(globalThis, "localStorage", {
  value: {
    getItem: (key: string) => _localStore[key] ?? null,
    setItem: (key: string, value: string) => {
      _localStore[key] = value;
    },
    removeItem: (key: string) => {
      Reflect.deleteProperty(_localStore, key);
    },
    clear: () => {
      Object.keys(_localStore).forEach((k) =>
        Reflect.deleteProperty(_localStore, k),
      );
    },
    get length() {
      return Object.keys(_localStore).length;
    },
    key: (index: number) => Object.keys(_localStore)[index] ?? null,
  } satisfies Storage,
  writable: true,
  configurable: true,
});

/* Provide a minimal matchMedia stub */
if (typeof globalThis.matchMedia === "undefined") {
  globalThis.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
