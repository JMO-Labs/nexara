/**
 * @file middleware/auth.global.ts
 * @brief Global route guard for authentication.
 *
 * Protects all `/app/**` routes by checking the auth store.
 * Unauthenticated users are redirected to `/auth/login` with the
 * original path saved as a `redirect` query parameter.
 * Authenticated users visiting `/auth/*` are redirected to `/app`.
 *
 * On cold page loads (no token in memory) we attempt a silent session
 * restore via the HttpOnly refresh cookie before blocking access.
 */

import { useAuthStore } from '~/stores/auth'

/**
 * @brief Pure auth decision logic (no Nuxt dependency).
 *
 * Exported separately so unit tests can call it without mocking
 * `navigateTo` or `defineNuxtRouteMiddleware`.
 *
 * @param to  - Target route object.
 * @param _from - Source route object (unused).
 * @returns A redirect descriptor or undefined to allow navigation.
 */
export function authMiddleware(
  to: { path: string; fullPath?: string },
  _from: { path: string },
): { path: string; query?: Record<string, string> } | undefined {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.isAuthenticated
  const path = to.path

  const isAppRoute = path.startsWith('/app')
  const isAuthRoute = path.startsWith('/auth')

  if (isAppRoute && !isAuthenticated) {
    return { path: '/auth/login', query: { redirect: to.fullPath || path } }
  }

  if (isAuthRoute && isAuthenticated) {
    return { path: '/app' }
  }

  return undefined
}

/** @brief Tracks whether a session restore has already been attempted. */
let sessionRestoreAttempted = false

/**
 * @brief Nuxt global middleware that wraps authMiddleware with proper
 *        navigation calls and a one-time silent session restore.
 */
export default defineNuxtRouteMiddleware(async (to, from) => {
  if (import.meta.server) return

  const authStore = useAuthStore()

  if (!authStore.isAuthenticated && !sessionRestoreAttempted) {
    sessionRestoreAttempted = true
    try {
      await authStore.refresh()
      if (authStore.accessToken) {
        await authStore.fetchUser()
      }
    } catch {
      /* Refresh failed -- user is genuinely unauthenticated */
    }
  }

  const result = authMiddleware(to, from)

  if (result) {
    return navigateTo(
      { path: result.path, query: result.query },
      { replace: true, redirectCode: 302 },
    )
  }
})
