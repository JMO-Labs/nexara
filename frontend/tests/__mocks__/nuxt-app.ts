/**
 * @file tests/__mocks__/nuxt-app.ts
 * @brief Mock for Nuxt #app auto-imports used in tests.
 *
 * Provides stub implementations of navigateTo, useRuntimeConfig,
 * useRoute, and useRouter so stores and composables can be tested
 * without a running Nuxt instance.
 */

export const navigateTo = (path: string) => ({ path })

export const useRuntimeConfig = () => ({
  public: {
    apiBaseUrl: '/api/v1',
  },
})

export const useRoute = () => ({
  path: '/',
  params: {},
  query: {},
  fullPath: '/',
})

export const useRouter = () => ({
  push: (path: string) => ({ path }),
  replace: (path: string) => ({ path }),
  currentRoute: { value: useRoute() },
})

export const defineNuxtRouteMiddleware = (fn: (...args: unknown[]) => unknown) => fn
export const definePageMeta = (_meta: Record<string, unknown>) => { /* no-op in tests */ }
