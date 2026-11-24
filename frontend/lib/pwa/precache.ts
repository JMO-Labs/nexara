/**
 * @file lib/pwa/precache.ts
 * @brief On a first visit the page and its chunks load before the service
 *        worker controls it, so nothing is cached for offline. Once a
 *        controller exists, report the current page + loaded static assets
 *        so the SW can store them ({type:"CACHE_URLS"}).
 */

const STATIC_RE = /^\/_next\/static\/|\.(woff2?|ttf|otf)$/;

/** @return current path + same-origin /_next/static and font resource URLs */
export function collectCacheUrls(): string[] {
  const urls = [location.pathname + location.search];
  const entries =
    typeof performance !== "undefined" && performance.getEntriesByType
      ? performance.getEntriesByType("resource")
      : [];
  for (const e of entries) {
    try {
      const u = new URL(e.name, location.href);
      if (u.origin === location.origin && STATIC_RE.test(u.pathname))
        urls.push(u.pathname + u.search);
    } catch {
      /* ignore */
    }
  }
  return [...new Set(urls)];
}

/** @brief Post CACHE_URLS to the active controller, if any. */
export function postCacheUrls(): void {
  const ctl = navigator.serviceWorker?.controller;
  if (ctl) ctl.postMessage({ type: "CACHE_URLS", urls: collectCacheUrls() });
}

/**
 * @brief Post once the SW is ready and controlling; if it only takes control
 *        later (first install claims the page), post on the first
 *        controllerchange instead.
 * @return cleanup
 */
export function startPrecache(): () => void {
  const sw = typeof navigator !== "undefined" ? navigator.serviceWorker : null;
  if (!sw) return () => {};
  let posted = false;
  const post = () => {
    if (posted || !sw.controller) return;
    posted = true;
    postCacheUrls();
  };
  sw.ready.then(post).catch(() => {});
  sw.addEventListener("controllerchange", post, { once: true });
  return () => sw.removeEventListener("controllerchange", post);
}
