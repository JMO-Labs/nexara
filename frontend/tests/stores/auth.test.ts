/**
 * @file tests/stores/auth.test.ts
 * @brief TDD tests for the auth Pinia store.
 *
 * Tests login/logout/refresh actions and state transitions.
 * Login now issues two fetches: POST /auth/login then GET /users/me.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '~/stores/auth'
import type { LoginResponse, RefreshResponse, User } from '~/types/api'

/** @brief User profile returned by GET /users/me. */
const mockUser: User = {
  id: '1',
  email: 'alice@example.com',
  username: 'alice',
  display_name: 'Alice',
  email_verified: true,
  avatar_url: null,
  bio: null,
  pronouns: null,
  location: null,
  website_url: null,
  birthday: null,
  role: 'member',
  totp_enabled: false,
  storage_used: 0,
  storage_quota: 1073741824,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  last_seen_at: null,
}

/** @brief Successful login response (no user, matches backend schema). */
const mockLoginResponse: LoginResponse = {
  access_token: 'jwt-token-123',
  token_type: 'bearer',
  expires_in: 1800,
  requires_2fa: false,
  two_factor_token: null,
}

const mockRefreshResponse: RefreshResponse = {
  access_token: 'jwt-token-456',
  token_type: 'bearer',
  expires_in: 1800,
}

/**
 * @brief Helper that mocks the two-step login flow: POST login + GET /users/me.
 */
function mockLoginFetches(): void {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify(mockLoginResponse), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(mockUser), { status: 200 }))
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('starts with unauthenticated state', () => {
    const store = useAuthStore()

    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('login() stores user and access token', async () => {
    const store = useAuthStore()
    mockLoginFetches()

    await store.login({ email: 'alice@example.com', password: 'secret123456' })

    expect(store.user).toEqual(mockUser)
    expect(store.accessToken).toBe('jwt-token-123')
    expect(store.isAuthenticated).toBe(true)
  })

  it('login() sets requiresTwoFactor when backend responds with 2FA', async () => {
    const store = useAuthStore()
    const twoFactorResponse: LoginResponse = {
      access_token: null,
      token_type: 'bearer',
      expires_in: null,
      requires_2fa: true,
      two_factor_token: '2fa-tok-abc',
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(twoFactorResponse), { status: 200 }),
    )

    await store.login({ email: 'alice@example.com', password: 'secret123456' })

    expect(store.requiresTwoFactor).toBe(true)
    expect(store.twoFactorToken).toBe('2fa-tok-abc')
    expect(store.isAuthenticated).toBe(false)
  })

  it('logout() clears state', async () => {
    const store = useAuthStore()
    mockLoginFetches()
    await store.login({ email: 'alice@example.com', password: 'secret123456' })

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    )
    await store.logout()

    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('refresh() updates the access token', async () => {
    const store = useAuthStore()
    mockLoginFetches()
    await store.login({ email: 'alice@example.com', password: 'secret123456' })

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockRefreshResponse), { status: 200 }),
    )
    await store.refresh()

    expect(store.accessToken).toBe('jwt-token-456')
    expect(store.user).toEqual(mockUser)
  })

  it('refresh() logs out on failure', async () => {
    const store = useAuthStore()
    mockLoginFetches()
    await store.login({ email: 'alice@example.com', password: 'secret123456' })

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await store.refresh()

    expect(store.isAuthenticated).toBe(false)
    expect(store.accessToken).toBeNull()
  })

  it('register() authenticates and fetches user profile', async () => {
    const store = useAuthStore()

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(mockLoginResponse), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(mockUser), { status: 200 }))

    await store.register({
      email: 'alice@example.com',
      username: 'alice',
      display_name: 'Alice',
      password: 'secret123456',
    })

    expect(store.accessToken).toBe('jwt-token-123')
    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)
  })
})
