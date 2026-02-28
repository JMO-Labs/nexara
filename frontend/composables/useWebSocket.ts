/**
 * @file composables/useWebSocket.ts
 * @brief WebSocket composable with first-message JWT auth and auto-reconnect.
 *
 * Establishes a persistent WebSocket connection to the backend at `/ws/`.
 * Authentication is performed by sending the JWT as the first message after
 * the connection opens. Implements exponential backoff reconnection
 * capped at 30 seconds.
 */

import { ref, onUnmounted } from "vue";
import { useAuthStore } from "~/stores/auth";

/** @brief Max reconnection delay in milliseconds. */
const MAX_BACKOFF_MS = 30_000;

/** @brief WebSocket connection states. */
export type WsStatus = "connecting" | "open" | "closed" | "error";

/**
 * @brief Creates a managed WebSocket connection with auth and reconnect.
 * @param onMessage - Callback invoked with parsed message data.
 * @returns Connection status ref and control functions.
 */
export function useWebSocket(onMessage: (data: unknown) => void) {
  const authStore = useAuthStore();
  const status = ref<WsStatus>("closed");

  let socket: WebSocket | null = null;
  let reconnectAttempt = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  /**
   * @brief Open the WebSocket connection and authenticate.
   */
  function connect(): void {
    if (disposed || !authStore.accessToken) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/`;

    status.value = "connecting";
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket?.send(
        JSON.stringify({ type: "auth", token: authStore.accessToken }),
      );
      status.value = "open";
      reconnectAttempt = 0;
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        /* Ignore malformed messages */
      }
    };

    socket.onclose = () => {
      status.value = "closed";
      scheduleReconnect();
    };

    socket.onerror = () => {
      status.value = "error";
      socket?.close();
    };
  }

  /** @brief Schedule a reconnection with exponential backoff. */
  function scheduleReconnect(): void {
    if (disposed) return;
    const delay = Math.min(1000 * 2 ** reconnectAttempt, MAX_BACKOFF_MS);
    reconnectAttempt++;
    reconnectTimer = setTimeout(connect, delay);
  }

  /** @brief Send a JSON message through the WebSocket. */
  function send(data: unknown): void {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(data));
    }
  }

  /** @brief Close the connection and stop reconnecting. */
  function disconnect(): void {
    disposed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    socket?.close();
    socket = null;
    status.value = "closed";
  }

  onUnmounted(disconnect);

  return { status, connect, disconnect, send };
}
