/**
 * @file composables/useApi.ts
 * @brief HTTP client composable with automatic auth token injection.
 *
 * Wraps the Fetch API with:
 * - Automatic `Authorization: Bearer <token>` header when authenticated
 * - 401 intercept -> token refresh -> single retry of the original request
 * - Redirect to login when refresh also fails
 * - JSON request/response convenience methods (get, post, put, delete)
 *
 * This is the only sanctioned way to call the backend API.
 * Never use raw `fetch()` directly in components or stores.
 */

import { useAuthStore } from '~/stores/auth'

/** @brief API base URL. */
const API_BASE = '/api/v1'

/** @brief Tracks whether a token refresh is already in-flight. */
let refreshPromise: Promise<void> | null = null

/**
 * @brief Creates an API client with auth-aware fetch methods.
 * @returns Object with get, post, put, and del methods.
 */
export function useApi() {
  const authStore = useAuthStore()

  /**
   * @brief Build headers with optional auth token.
   * @param extra - Additional headers to merge.
   */
  function buildHeaders(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = { ...extra }
    if (authStore.accessToken) {
      headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return headers
  }

  /**
   * @brief Core fetch wrapper with 401 retry logic.
   * @param path - API path relative to base URL.
   * @param options - Fetch options.
   * @param isRetry - Whether this is a retry after token refresh.
   */
  async function request<T>(
    path: string,
    options: RequestInit = {},
    isRetry = false,
  ): Promise<T> {
    const url = `${API_BASE}${path}`
    const response = await fetch(url, {
      ...options,
      credentials: 'include',
      headers: buildHeaders(options.headers as Record<string, string>),
    })

    if (response.status === 401 && !isRetry) {
      if (!refreshPromise) {
        refreshPromise = authStore.refresh().finally(() => { refreshPromise = null })
      }
      await refreshPromise

      if (!authStore.accessToken) {
        throw new Error('Session expired')
      }

      return request<T>(path, options, true)
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: { message: 'Request failed' } }))
      throw new Error(error?.error?.message || `HTTP ${response.status}`)
    }

    if (response.status === 204) return undefined as T
    return response.json()
  }

  /** @brief GET request. */
  async function get<T>(path: string): Promise<T> {
    return request<T>(path)
  }

  /** @brief POST request with JSON body. */
  async function post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  /** @brief PUT request with JSON body. */
  async function put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  /** @brief DELETE request. */
  async function del<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' })
  }

  return { get, post, put, del }
}
