/**
 * @file tests/composables/useApi.test.ts
 * @brief TDD tests for the useApi composable.
 *
 * Verifies authorization header injection, 401 intercept with
 * token refresh and request retry, and redirect on refresh failure.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '~/stores/auth'
import { useApi } from '~/composables/useApi'

describe('useApi', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('attaches Authorization header when token exists', async () => {
    const authStore = useAuthStore()
    authStore.accessToken = 'test-token'

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    const api = useApi()
    await api.get('/test')

    const calledHeaders = fetchSpy.mock.calls[0][1]?.headers as Record<string, string>
    expect(calledHeaders?.Authorization).toBe('Bearer test-token')
  })

  it('does not attach Authorization header when no token', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    const api = useApi()
    await api.get('/test')

    const calledHeaders = fetchSpy.mock.calls[0][1]?.headers as Record<string, string>
    expect(calledHeaders?.Authorization).toBeUndefined()
  })

  it('retries request after refreshing token on 401', async () => {
    const authStore = useAuthStore()
    authStore.accessToken = 'expired-token'

    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'new-token', token_type: 'bearer' }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: 'success' }), { status: 200 }),
      )

    const api = useApi()
    const result = await api.get('/protected')

    expect(result).toEqual({ data: 'success' })
    expect(fetchSpy).toHaveBeenCalledTimes(3)
  })

  it('throws on 401 when refresh also fails', async () => {
    const authStore = useAuthStore()
    authStore.accessToken = 'expired-token'

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 }))

    const api = useApi()

    await expect(api.get('/protected')).rejects.toThrow()
    expect(authStore.isAuthenticated).toBe(false)
  })

  it('sends POST with JSON body', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ id: '1' }), { status: 201 }),
    )

    const api = useApi()
    await api.post('/items', { name: 'test' })

    expect(fetchSpy.mock.calls[0][1]?.method).toBe('POST')
    expect(fetchSpy.mock.calls[0][1]?.body).toBe(JSON.stringify({ name: 'test' }))
  })
})
