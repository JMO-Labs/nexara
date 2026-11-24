/**
 * @file lib/pwa/queryPersist.ts
 * @brief Persists the TanStack Query cache to IndexedDB (idb-keyval) so the
 *        last-viewed data renders offline. Async persister chosen over the
 *        localStorage one: ~5MB localStorage quota is too small for feeds.
 */
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import type { Query } from "@tanstack/react-query";
import { del, get, set } from "idb-keyval";

export const PERSIST_KEY = "nx-rq-cache";
export const PERSIST_MAX_AGE = 24 * 60 * 60 * 1000;
/** Build id used as cache buster (see next.config.ts). */
export const PERSIST_BUSTER = process.env.NEXT_PUBLIC_BUILD_ID ?? "dev";

/** Query-key prefixes holding auth, secrets or admin data: never persisted. */
const DENY = new Set([
  "auth",
  "2fa",
  "admin",
  "passkeys",
  "data-export",
  "storage",
  "push",
  "apprise",
  "settings",
  "plugins",
  "invites",
  "sso",
  "oauth",
]);

/** @brief Only successful, non-sensitive queries are dehydrated. */
export function shouldPersist(
  query: Pick<Query, "queryKey" | "state">,
): boolean {
  if (query.state.status !== "success") return false;
  const head = query.queryKey[0];
  return !(typeof head === "string" && DENY.has(head));
}

const hasIdb = () => typeof indexedDB !== "undefined";

/** @brief IndexedDB-backed persister, or null where IndexedDB is missing. */
export function createPersister() {
  if (!hasIdb()) return null;
  return createAsyncStoragePersister({
    key: PERSIST_KEY,
    throttleTime: 2000,
    storage: {
      getItem: (k) => get<string>(k).then((v) => v ?? null),
      setItem: (k, v) => set(k, v),
      removeItem: (k) => del(k),
    },
  });
}

/** @brief Delete the persisted cache (logout / login / account switch). */
export function clearPersistedQueries(): Promise<void> {
  if (!hasIdb()) return Promise.resolve();
  return del(PERSIST_KEY).catch(() => {});
}
