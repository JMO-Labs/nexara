/**
 * @file lib/pwa/clearUserCache.ts
 * @brief Drop SW-saved authenticated pages on sign-out / login / account switch.
 */

/**
 * @brief Ask the SW to purge its pages cache; delete directly when no
 *        controller is active (SW absent or not yet controlling).
 */
export function clearUserCache(): void {
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
