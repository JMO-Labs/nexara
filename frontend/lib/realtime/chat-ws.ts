/**
 * @file lib/realtime/chat-ws.ts
 * @brief Singleton WebSocket manager for chat. JWT first-frame auth,
 *        exponential backoff reconnect, heartbeat, fanout to subscribers.
 */
import {
  API_BASE,
  getAccessToken,
  onAuthChange,
  refreshAccessToken,
} from "@/lib/auth/session";

const WS_URL_OVERRIDE =
  process.env.NEXT_PUBLIC_WS_URL ?? process.env.NEXT_PUBLIC_WS_BASE_URL ?? "";
const DEV_BACKEND_PORT = process.env.NEXT_PUBLIC_DEV_BACKEND_PORT ?? "8000";

function deriveWsUrl(): string {
  if (WS_URL_OVERRIDE) {
    return WS_URL_OVERRIDE.replace(/\/$/, "") + "/ws/";
  }
  if (typeof window === "undefined") return "";

  // If an absolute API base is configured, use it directly.
  if (API_BASE) {
    return API_BASE.replace(/^http/, "ws").replace(/\/$/, "") + "/ws/";
  }

  // Same-origin fallback. Next.js rewrites do NOT proxy WebSocket upgrades
  // in dev — when running on localhost, target the FastAPI port directly.
  const { protocol, hostname, host } = window.location;
  const wsProto = protocol === "https:" ? "wss:" : "ws:";
  const isLocal =
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "0.0.0.0";
  const target = isLocal ? `${hostname}:${DEV_BACKEND_PORT}` : host;
  return `${wsProto}//${target}/ws/`;
}

export type WsStatus = "connecting" | "open" | "closed" | "error";

export interface WsFrame {
  type: string;
  payload?: Record<string, unknown>;
}

type Listener = (frame: WsFrame) => void;
type StatusListener = (status: WsStatus) => void;

const MAX_BACKOFF = 30_000;
const HEARTBEAT_MS = 25_000;

class ChatWsManager {
  private socket: WebSocket | null = null;
  private status: WsStatus = "closed";
  private attempt = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private refCount = 0;
  private listeners = new Set<Listener>();
  private statusListeners = new Set<StatusListener>();
  private authed = false;
  private offAuth: (() => void) | null = null;
  private idleTimer: ReturnType<typeof setTimeout> | null = null;

  acquire(): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
    this.refCount++;
    if (this.refCount === 1) {
      this.offAuth = onAuthChange((tok) => {
        if (tok && this.refCount > 0 && !this.socket) this.connect();
      });
      this.connect();
    }
  }

  release(): void {
    this.refCount = Math.max(0, this.refCount - 1);
    if (this.refCount === 0) {
      // Debounce disconnect — StrictMode dev double-mount causes
      // acquire→release→acquire within microtasks; tearing the socket
      // down each cycle wastes the JWT auth handshake.
      if (this.idleTimer) clearTimeout(this.idleTimer);
      this.idleTimer = setTimeout(() => {
        this.idleTimer = null;
        if (this.refCount === 0) {
          this.offAuth?.();
          this.offAuth = null;
          this.disconnect();
        }
      }, 250);
    }
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  onStatus(fn: StatusListener): () => void {
    this.statusListeners.add(fn);
    fn(this.status);
    return () => this.statusListeners.delete(fn);
  }

  send(frame: WsFrame): void {
    if (this.socket?.readyState === WebSocket.OPEN && this.authed) {
      this.socket.send(JSON.stringify(frame));
    }
  }

  private setStatus(s: WsStatus): void {
    this.status = s;
    for (const l of this.statusListeners) l(s);
  }

  private async connect(): Promise<void> {
    if (typeof window === "undefined") return;
    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) return;

    this.setStatus("connecting");
    this.authed = false;

    let token = getAccessToken();
    if (!token) token = await refreshAccessToken();
    if (!token || this.refCount === 0) {
      this.setStatus("closed");
      return;
    }

    const wsUrl = deriveWsUrl();
    if (process.env.NODE_ENV !== "production") {
      console.debug("[chat-ws] connecting to", wsUrl);
    }
    if (!wsUrl) {
      this.setStatus("closed");
      return;
    }

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch (err) {
      console.error("[chat-ws] connect failed", err);
      this.setStatus("error");
      this.scheduleReconnect();
      return;
    }
    this.socket = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "auth", payload: { token } }));
    };

    ws.onmessage = (event) => {
      let data: WsFrame;
      try {
        data = JSON.parse(event.data) as WsFrame;
      } catch {
        return;
      }
      if (data.type === "auth_ok") {
        this.authed = true;
        this.attempt = 0;
        this.setStatus("open");
        this.startHeartbeat();
        return;
      }
      if (data.type === "auth_error") {
        this.authed = false;
        return;
      }
      for (const l of this.listeners) l(data);
    };

    ws.onerror = (err) => {
      console.error("[chat-ws] error", err);
      this.setStatus("error");
    };

    ws.onclose = (ev) => {
      if (process.env.NODE_ENV !== "production") {
        console.debug("[chat-ws] closed", ev.code, ev.reason);
      }
      this.authed = false;
      this.stopHeartbeat();
      this.setStatus("closed");
      this.socket = null;
      if (this.refCount > 0) this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (this.retryTimer) clearTimeout(this.retryTimer);
    const delay = Math.min(1000 * 2 ** this.attempt, MAX_BACKOFF);
    this.attempt++;
    this.retryTimer = setTimeout(() => this.connect(), delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: "ping" });
    }, HEARTBEAT_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = null;
  }

  private disconnect(): void {
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.retryTimer = null;
    this.stopHeartbeat();
    this.socket?.close();
    this.socket = null;
    this.authed = false;
    this.setStatus("closed");
  }
}

export const chatWs = new ChatWsManager();
