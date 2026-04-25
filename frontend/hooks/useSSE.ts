'use client';
/**
 * @file hooks/useSSE.ts
 * @brief Long-lived EventSource subscription to /notifications/stream.
 *        EventSource cannot send custom headers, so the access token is
 *        passed as a query param (matches existing backend contract).
 *        Reconnects on error with exponential backoff capped at 30s and
 *        replays Last-Event-ID on reconnect.
 */
import { useEffect, useRef } from 'react';
import { API_BASE, getAccessToken, refreshAccessToken } from '@/lib/auth/session';

export interface SSEOptions {
  enabled?: boolean;
  onMessage?: (data: unknown, type: string) => void;
  onError?: (err: unknown) => void;
  /** Named SSE event types to subscribe to via addEventListener. */
  eventTypes?: readonly string[];
}

export function useSSE(path: string, opts: SSEOptions = {}): void {
  const { enabled = true, onMessage, onError, eventTypes } = opts;
  const eventTypesKey = (eventTypes ?? []).join(',');
  const lastEventId = useRef<string | null>(null);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
  }, [onMessage, onError]);

  useEffect(() => {
    if (!enabled || typeof EventSource === 'undefined') return;

    let es: EventSource | null = null;
    let retryDelay = 1000;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connect = async () => {
      if (cancelled) return;
      let token = getAccessToken();
      if (!token) token = await refreshAccessToken();
      if (!token || cancelled) return;

      const base = API_BASE || (typeof window !== 'undefined' ? window.location.origin : '');
      const url = new URL(`${base}${path}`);
      url.searchParams.set('token', token);
      if (lastEventId.current) {
        url.searchParams.set('last_event_id', lastEventId.current);
      }

      es = new EventSource(url.toString(), { withCredentials: true });

      const dispatch = (ev: MessageEvent, type: string) => {
        if (ev.lastEventId) lastEventId.current = ev.lastEventId;
        try {
          const parsed = JSON.parse(ev.data);
          onMessageRef.current?.(parsed, type);
        } catch {
          onMessageRef.current?.(ev.data, type);
        }
      };
      es.onmessage = (ev) => dispatch(ev, 'message');
      for (const t of eventTypes ?? []) {
        es.addEventListener(t, (ev) => dispatch(ev as MessageEvent, t));
      }

      es.onerror = (err) => {
        onErrorRef.current?.(err);
        es?.close();
        es = null;
        if (cancelled) return;
        retryTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 30_000);
      };

      es.onopen = () => {
        retryDelay = 1000;
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      es?.close();
    };
    // eventTypes captured via eventTypesKey; ref pattern keeps callbacks fresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, enabled, eventTypesKey]);
}
