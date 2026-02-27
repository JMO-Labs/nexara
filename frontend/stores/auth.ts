/**
 * @file stores/auth.ts
 * @brief Pinia store for authentication state management.
 *
 * Manages the user session: access token (memory only), current user profile,
 * login/logout/refresh actions. The refresh token is stored as an HttpOnly
 * cookie by the backend -- the frontend never touches it directly.
 *
 * After login/register the backend returns only tokens (no user object),
 * so we issue a follow-up GET /users/me to populate the user state.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { User, LoginRequest, LoginResponse, RefreshResponse } from '~/types/api'

/** @brief API base URL for auth endpoints. */
const API_BASE = '/api/v1'

/**
 * @brief Extract a human-readable message from the backend error envelope.
 *
 * The backend returns `{ error: { code, message, details } }` where `details`
 * is a field->message map for validation errors.
 */
function formatApiError(body: Record<string, unknown>, fallback: string): string {
  const envelope = body?.error as Record<string, unknown> | undefined
  if (!envelope) return (body?.detail as string) || fallback

  const details = envelope.details as Record<string, string> | undefined
  if (details && typeof details === 'object') {
    const msgs = Object.entries(details).map(([field, msg]) => {
      const name = field.replace(/^body\./, '')
      return `${name}: ${msg}`
    })
    return msgs.join('; ')
  }

  return (envelope.message as string) || fallback
}

export const useAuthStore = defineStore('auth', () => {
  /** @brief Current authenticated user or null. */
  const user = ref<User | null>(null)

  /** @brief JWT access token kept in memory only (never localStorage). */
  const accessToken = ref<string | null>(null)

  /** @brief Whether the backend requires 2FA verification to complete login. */
  const requiresTwoFactor = ref(false)

  /** @brief Opaque 2FA token returned when requires_2fa is true. */
  const twoFactorToken = ref<string | null>(null)

  /** @brief Whether the user is fully authenticated. */
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  /**
   * @brief Fetch the authenticated user's profile from GET /users/me.
   * @throws Error if the request fails.
   */
  async function fetchUser(): Promise<void> {
    const response = await fetch(`${API_BASE}/users/me`, {
      credentials: 'include',
      headers: accessToken.value
        ? { Authorization: `Bearer ${accessToken.value}` }
        : {},
    })
    if (!response.ok) {
      throw new Error('Failed to fetch user profile')
    }
    user.value = await response.json()
  }

  /**
   * @brief Authenticate with email and password.
   * @param credentials - Email and password payload.
   */
  async function login(credentials: LoginRequest): Promise<void> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(credentials),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(formatApiError(error, 'Login failed'))
    }

    const data: LoginResponse = await response.json()

    if (data.requires_2fa) {
      requiresTwoFactor.value = true
      twoFactorToken.value = data.two_factor_token
      accessToken.value = null
      user.value = null
      return
    }

    requiresTwoFactor.value = false
    twoFactorToken.value = null
    accessToken.value = data.access_token
    await fetchUser()
  }

  /**
   * @brief Complete 2FA verification and finish login.
   * @param code - TOTP code or backup code.
   * @param isBackup - Whether this is a backup code.
   */
  async function verify2fa(code: string, isBackup = false): Promise<void> {
    const body: Record<string, string> = isBackup
      ? { backup_code: code }
      : { code }

    if (twoFactorToken.value) {
      body.two_factor_token = twoFactorToken.value
    }

    const response = await fetch(`${API_BASE}/auth/2fa/verify-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(formatApiError(error, 'Verification failed'))
    }

    const data: LoginResponse = await response.json()
    requiresTwoFactor.value = false
    twoFactorToken.value = null
    accessToken.value = data.access_token
    await fetchUser()
  }

  /**
   * @brief Register a new user and auto-login on success.
   * @param payload - Registration fields.
   */
  async function register(payload: {
    email: string
    username: string
    display_name: string
    password: string
    invite_token?: string
  }): Promise<void> {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(formatApiError(error, 'Registration failed'))
    }

    const data: LoginResponse = await response.json()
    accessToken.value = data.access_token
    await fetchUser()
  }

  /**
   * @brief Log out the current user.
   *
   * Calls the backend to revoke the refresh token cookie,
   * then clears all local state.
   */
  async function logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: accessToken.value
          ? { Authorization: `Bearer ${accessToken.value}` }
          : {},
      })
    } catch {
      /* Logout endpoint failure is non-critical */
    }

    user.value = null
    accessToken.value = null
    requiresTwoFactor.value = false
    twoFactorToken.value = null
  }

  /**
   * @brief Refresh the access token using the HttpOnly refresh cookie.
   *
   * On failure, the user is logged out and state is cleared.
   */
  async function refresh(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })

      if (!response.ok) {
        await logout()
        return
      }

      const data: RefreshResponse = await response.json()
      accessToken.value = data.access_token
    } catch {
      await logout()
    }
  }

  return {
    user,
    accessToken,
    requiresTwoFactor,
    twoFactorToken,
    isAuthenticated,
    fetchUser,
    login,
    verify2fa,
    register,
    logout,
    refresh,
  }
})
