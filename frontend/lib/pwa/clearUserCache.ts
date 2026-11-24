/**
 * @file lib/pwa/clearUserCache.ts
 * @brief Drop SW-saved authenticated pages on sign-out / login / account switch.
 */
import { clearPersistedQueries } from "./queryPersist";

/** Window event telling Providers to empty the in-memory query cache. */
export const CLEAR_EVENT = "nx:clear-user-cache";

/**
 * @brief Ask the SW to purge its pages cache; delete directly when no
 *        controller is active (SW absent or not yet controlling).
 */
export function clearUserCache(): void {
  // Drop the in-memory query cache first (Providers listens), then the
  // persisted copy, so a throttled write cannot resurrect old data.
  try {
    window.dispatchEvent(new Event(CLEAR_EVENT));
  } catch {
    /* no window */
  }
  void clearPersistedQueries();
  try {
    const ctl =
      typeof navigator !== "undefined"
        ? navigator.serviceWorker?.controller
        : null;
    if (ctl) {
      ctl.postMessage({ type: "CLEAR_USER_CACHE" });
      return;
    }
    if (typeof caches !== "undefined") {
      caches
        .keys()
        .then((ks) =>
          Promise.all(
            ks.filter((k) => k.endsWith("-pages")).map((k) => caches.delete(k)),
          ),
        )
        .catch(() => {});
    }
  } catch {
    /* best effort */
  }
}
