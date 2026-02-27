/**
 * @file composables/useSSE.ts
 * @brief SSE (Server-Sent Events) composable for real-time notifications and feed updates.
 *
 * Connects to the backend SSE endpoint at `/api/v1/notifications/stream`
 * with Bearer token auth. Supports Last-Event-ID for reconnection and
 * automatic retry on connection loss.
 */

import { ref, onUnmounted } from 'vue'
import { useAuthStore } from '~/stores/auth'

/** @brief SSE connection states. */
export type SseStatus = 'connecting' | 'open' | 'closed' | 'error'

/**
 * @brief Creates a managed SSE connection with auth and auto-reconnect.
 * @param onEvent - Callback invoked with event type and parsed data.
 * @returns Connection status ref and control functions.
 */
export function useSSE(onEvent: (type: string, data: unknown) => void) {
  const authStore = useAuthStore()
  const status = ref<SseStatus>('closed')

  let eventSource: EventSource | null = null
  let lastEventId: string | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let disposed = false

  /**
   * @brief Open the SSE connection.
   *
   * Uses a polyfill-friendly approach: since the native EventSource API
   * does not support custom headers, the token is passed as a query
   * parameter. The backend accepts both header and query param auth
   * for SSE endpoints.
   */
  function connect(): void {
    if (disposed || !authStore.accessToken) return

    const params = new URLSearchParams({ token: authStore.accessToken })
    if (lastEventId) params.set('last_event_id', lastEventId)

    const url = `/api/v1/notifications/stream?${params}`

    status.value = 'connecting'
    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      status.value = 'open'
    }

    eventSource.onmessage = (event) => {
      if (event.lastEventId) lastEventId = event.lastEventId
      try {
        const data = JSON.parse(event.data)
        onEvent('message', data)
      } catch {
        /* Ignore malformed messages */
      }
    }

    eventSource.addEventListener('feed_update', (event) => {
      const msgEvent = event as MessageEvent
      if (msgEvent.lastEventId) lastEventId = msgEvent.lastEventId
      try {
        const data = JSON.parse(msgEvent.data)
        onEvent('feed_update', data)
      } catch {
        /* Ignore malformed messages */
      }
    })

    eventSource.addEventListener('notification', (event) => {
      const msgEvent = event as MessageEvent
      if (msgEvent.lastEventId) lastEventId = msgEvent.lastEventId
      try {
        const data = JSON.parse(msgEvent.data)
        onEvent('notification', data)
      } catch {
        /* Ignore malformed messages */
      }
    })

    eventSource.onerror = () => {
      status.value = 'error'
      eventSource?.close()
      scheduleReconnect()
    }
  }

  /** @brief Reconnect after a brief delay. */
  function scheduleReconnect(): void {
    if (disposed) return
    reconnectTimer = setTimeout(connect, 5000)
  }

  /** @brief Close the connection and stop reconnecting. */
  function disconnect(): void {
    disposed = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    eventSource?.close()
    eventSource = null
    status.value = 'closed'
  }

  onUnmounted(disconnect)

  return { status, connect, disconnect }
}
