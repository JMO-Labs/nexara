/**
 * @file middleware/auth.global.ts
 * @brief Global route guard for authentication.
 *
 * Protects all `/app/**` routes by checking the auth store.
 * Unauthenticated users are redirected to `/auth/login` with the
 * original path saved as a `redirect` query parameter.
 * Authenticated users visiting `/auth/*` are redirected to `/app`.
 */

import { useAuthStore } from '~/stores/auth'

/** @brief Routes that do not require authentication. */
const PUBLIC_PREFIXES = ['/', '/auth']

/**
 * @brief Auth middleware function.
 *
 * Exported separately for unit testing. In production this is registered
 * as a Nuxt global middleware via the file naming convention.
 *
 * @param to - Target route object.
 * @param _from - Source route object (unused).
 * @returns Navigation redirect or undefined to proceed.
 */
export function authMiddleware(
  to: { path: string; fullPath?: string },
  _from: { path: string },
): { path: string; query?: Record<string, string> } | undefined {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.isAuthenticated
  const path = to.path

  const isPublicRoute = path === '/'
    || path.startsWith('/auth')
    || PUBLIC_PREFIXES.some(prefix => prefix !== '/' && prefix !== '/auth' && path.startsWith(prefix))

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

/**
 * @brief Nuxt route middleware definition.
 *
 * Wraps authMiddleware for Nuxt's defineNuxtRouteMiddleware convention.
 */
export default function (to: { path: string; fullPath?: string }, from: { path: string }) {
  return authMiddleware(to, from)
}
