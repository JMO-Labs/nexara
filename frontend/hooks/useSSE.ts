"use client";
/**
 * @file hooks/useSSE.ts
 * @brief Long-lived EventSource subscription to /notifications/stream.
 *        EventSource cannot send custom headers, so the access token is
 *        passed as a query param (matches existing backend contract).
 *        Reconnects on error with exponential backoff capped at 30s and
 *        replays Last-Event-ID on reconnect. One EventSource is shared per
 *        path across all subscribers (ref-counted); the last unsubscribe
 *        closes it.
 */
import { useEffect, useRef } from "react";
import {
  API_BASE,
  getAccessToken,
  refreshAccessToken,
} from "@/lib/auth/session";

export interface SSEOptions {
  enabled?: boolean;
  onMessage?: (data: unknown, type: string) => void;
  onError?: (err: unknown) => void;
  /** Named SSE event types to subscribe to via addEventListener. */
  eventTypes?: readonly string[];
}

interface Subscriber {
  types: ReadonlySet<string>;
  onMessage: () => SSEOptions["onMessage"];
  onError: () => SSEOptions["onError"];
}

interface Shared {
  subs: Set<Subscriber>;
  es: EventSource | null;
  registered: Set<string>;
  lastEventId: string | null;
  retryDelay: number;
  retryTimer: ReturnType<typeof setTimeout> | null;
  closed: boolean;
}

const shared = new Map<string, Shared>();

function dispatch(entry: Shared, ev: MessageEvent, type: string) {
  if (ev.lastEventId) entry.lastEventId = ev.lastEventId;
  let data: unknown;
  try {
    data = JSON.parse(ev.data);
  } catch {
    data = ev.data;
  }
  entry.subs.forEach((s) => {
    if (type === "message" || s.types.has(type)) s.onMessage()?.(data, type);
  });
}

function register(entry: Shared, type: string) {
  if (entry.registered.has(type) || !entry.es) return;
  entry.registered.add(type);
  entry.es.addEventListener(type, (ev) =>
    dispatch(entry, ev as MessageEvent, type),
  );
}

async function connect(path: string, entry: Shared) {
  if (entry.closed) return;
  let token = getAccessToken();
  if (!token) token = await refreshAccessToken();
  if (!token || entry.closed) return;

  const base =
    API_BASE || (typeof window !== "undefined" ? window.location.origin : "");
  const url = new URL(`${base}${path}`);
  url.searchParams.set("token", token);
  if (entry.lastEventId) {
    url.searchParams.set("last_event_id", entry.lastEventId);
  }

  const es = new EventSource(url.toString(), { withCredentials: true });
  entry.es = es;
  entry.registered = new Set();
  es.onmessage = (ev) => dispatch(entry, ev, "message");
  entry.subs.forEach((s) => s.types.forEach((t) => register(entry, t)));

  es.onerror = (err) => {
    entry.subs.forEach((s) => s.onError()?.(err));
    es.close();
    entry.es = null;
    if (entry.closed) return;
    entry.retryTimer = setTimeout(() => connect(path, entry), entry.retryDelay);
    entry.retryDelay = Math.min(entry.retryDelay * 2, 30_000);
  };
  es.onopen = () => {
    entry.retryDelay = 1000;
  };
}

function subscribe(path: string, sub: Subscriber): () => void {
  let entry = shared.get(path);
  if (!entry) {
    entry = {
      subs: new Set(),
      es: null,
      registered: new Set(),
      lastEventId: null,
      retryDelay: 1000,
      retryTimer: null,
      closed: false,
    };
    shared.set(path, entry);
    entry.subs.add(sub);
    void connect(path, entry);
  } else {
    entry.subs.add(sub);
    sub.types.forEach((t) => register(entry!, t));
  }
  const e = entry;
  return () => {
    e.subs.delete(sub);
    if (e.subs.size > 0) return;
    e.closed = true;
    if (e.retryTimer) clearTimeout(e.retryTimer);
    e.es?.close();
    if (shared.get(path) === e) shared.delete(path);
  };
}

export function useSSE(path: string, opts: SSEOptions = {}): void {
  const { enabled = true, onMessage, onError, eventTypes } = opts;
  const eventTypesKey = (eventTypes ?? []).join(",");
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
  }, [onMessage, onError]);

  useEffect(() => {
    if (!enabled || typeof EventSource === "undefined") return;
    return subscribe(path, {
      types: new Set(eventTypesKey ? eventTypesKey.split(",") : []),
      onMessage: () => onMessageRef.current,
      onError: () => onErrorRef.current,
    });
    // eventTypes tracked via eventTypesKey; refs keep callbacks fresh.
  }, [path, enabled, eventTypesKey]);
}
