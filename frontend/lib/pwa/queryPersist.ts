/**
 * @file lib/pwa/queryPersist.ts
 * @brief Persists the TanStack Query cache to IndexedDB (idb-keyval) so the
 *        last-viewed data renders offline. Async persister chosen over the
 *        localStorage one: ~5MB localStorage quota is too small for feeds.
 */
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import type { Query } from "@tanstack/react-query";
import type { Persister } from "@tanstack/react-query-persist-client";
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

/** Key paths (first two segments) that carry secrets/tokens: never persisted. */
const DENY_PATH = new Set([
  "notifications/apprise",
  "notifications/webhooks",
  "notifications/preferences",
  "events/subscriptions",
  "users/sso",
]);

/** @brief Only successful, non-sensitive queries are dehydrated. */
export function shouldPersist(
  query: Pick<Query, "queryKey" | "state">,
): boolean {
  if (query.state.status !== "success") return false;
  const [head, second] = query.queryKey;
  if (typeof head === "string" && DENY.has(head)) return false;
  return !DENY_PATH.has(`${String(head)}/${String(second)}`);
}

const hasIdb = () => typeof indexedDB !== "undefined";

const always = () => true;

/**
 * @brief IndexedDB-backed persister, or null where IndexedDB is missing.
 * @param isLive gate: once false, reads return nothing (a stale restore is
 *        dropped) and writes are skipped (a late throttled save is dropped).
 */
export function createPersister(isLive: () => boolean = always) {
  if (!hasIdb()) return null;
  return createAsyncStoragePersister({
    key: PERSIST_KEY,
    throttleTime: 2000,
    storage: {
      getItem: (k) =>
        get<string>(k).then((v) => (isLive() ? (v ?? null) : null)),
      setItem: (k, v) => (isLive() ? set(k, v) : Promise.resolve()),
      removeItem: (k) => del(k),
    },
  });
}

/** @brief Delete the persisted cache (logout / login / account switch). */
export function clearPersistedQueries(): Promise<void> {
  if (!hasIdb()) return Promise.resolve();
  return del(PERSIST_KEY).catch(() => {});
}

const NOOP: Persister = {
  persistClient: async () => {},
  restoreClient: async () => undefined,
  removeClient: async () => {},
};

/**
 * @brief Persist options scoped to one user. Without a user id (or without
 *        IndexedDB) nothing is restored or persisted; the buster embeds the
 *        user id so another user never hydrates this user's blob.
 * @param userId session user id, if known
 * @param isLive see createPersister
 */
export function persistOptionsFor(
  userId?: string | null,
  isLive: () => boolean = always,
) {
  return {
    persister: (userId && createPersister(isLive)) || NOOP,
    maxAge: PERSIST_MAX_AGE,
    buster: `${PERSIST_BUSTER}:${userId ?? "anon"}`,
    dehydrateOptions: {
      shouldDehydrateQuery: shouldPersist,
      // Never persist mutations (paused ones carry variables like passwords).
      shouldDehydrateMutation: () => false,
    },
  };
}
