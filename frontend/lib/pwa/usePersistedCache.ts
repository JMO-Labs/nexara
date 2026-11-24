"use client";
/**
 * @file lib/pwa/usePersistedCache.ts
 * @brief Binds TanStack Query persistence to the signed-in user. Unlike
 *        PersistQueryClientProvider (options captured once at mount), this
 *        restores + subscribes per user id and tears down on change/logout.
 */
import { useEffect, useRef, useState } from "react";
import type { QueryClient } from "@tanstack/react-query";
import {
  persistQueryClientRestore,
  persistQueryClientSubscribe,
} from "@tanstack/react-query-persist-client";
import { persistOptionsFor } from "./queryPersist";
import { CLEAR_EVENT } from "./clearUserCache";

/**
 * @brief Restore then persist the query cache for `userId`.
 * @param client the app QueryClient (kept across users; cleared on purge)
 * @param userId session user id; none = no persistence
 * @return true while the user's cache is being restored (queries wait)
 */
export function usePersistedCache(
  client: QueryClient,
  userId?: string | null,
): boolean {
  // Bumped on purge so the same user re-binds a fresh persister.
  const [epoch, setEpoch] = useState(0);
  const [restored, setRestored] = useState<string | null>(null);
  const stop = useRef<() => void>(() => {});
  const key = `${userId}:${epoch}`;

  useEffect(() => {
    // Purge: stop persisting before clearing memory, so neither the clear
    // nor a pending throttled save can write after IndexedDB is deleted.
    const purge = () => {
      stop.current();
      client.clear();
      setEpoch((e) => e + 1);
    };
    window.addEventListener(CLEAR_EVENT, purge);
    return () => window.removeEventListener(CLEAR_EVENT, purge);
  }, [client]);

  useEffect(() => {
    if (!userId) return;
    let live = true;
    let unsubscribe = () => {};
    const opts = {
      queryClient: client,
      ...persistOptionsFor(userId, () => live),
    };
    const halt = () => {
      live = false;
      unsubscribe();
    };
    stop.current = halt;
    persistQueryClientRestore(opts)
      .catch(() => {})
      .then(() => {
        if (!live) return; // user changed mid-restore: drop it
        unsubscribe = persistQueryClientSubscribe(opts);
        setRestored(key);
      });
    return halt;
  }, [client, userId, key]);

  return !!userId && restored !== key;
}
