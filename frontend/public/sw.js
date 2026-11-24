/**
 * @file public/sw.js
 * @brief Nexara service worker. Cache-first for /_next/static + fonts,
 *        network-first (LRU, max 30) for navigations with /offline fallback,
 *        API never cached. Update flow: new SW waits until the page posts
 *        {type:"SKIP_WAITING"}. Web Push: shows notification, app badge, deep-link click.
 *        VERSION comes from /sw-version.js (written by next.config at build).
 */
let BUILD = "dev";
try {
  importScripts("/sw-version.js");
  if (self.__SW_VERSION__) BUILD = self.__SW_VERSION__;
} catch {
  /* dev: file missing */
}
const VERSION = "nexara-" + BUILD;
const PAGES = VERSION + "-pages";
const STATIC = VERSION + "-static";
const SHELL = ["/offline", "/manifest.webmanifest"];
const MAX_PAGES = 30;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(VERSION)
      .then((cache) => cache.addAll(SHELL))
      .catch(() => {}),
  );
});

self.addEventListener("message", (event) => {
  const type = event.data && event.data.type;
  if (type === "SKIP_WAITING") self.skipWaiting();
  // Sign-out / account switch: drop saved pages, shown notifications, badge.
  if (type === "CLEAR_USER_CACHE")
    event.waitUntil(
      Promise.all([
        caches.delete(PAGES),
        Promise.resolve(self.registration.getNotifications?.())
          .then((ns) => (ns || []).forEach((n) => n.close()))
          .catch(() => {}),
        Promise.resolve(self.navigator?.clearAppBadge?.()).catch(() => {}),
      ]),
    );
  // First load ran before the SW controlled the page: cache what it fetched.
  if (type === "CACHE_URLS") event.waitUntil(precache(event.data.urls));
});

self.addEventListener("activate", (event) => {
  const keep = [VERSION, PAGES, STATIC];
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => !keep.includes(k)).map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

/** @brief Static asset (build chunk or font) served cache-first. */
function isStatic(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    /\.(woff2?|ttf|otf)$/.test(url.pathname)
  );
}

/** @brief Cache same-origin static assets and /app pages the page reports. */
async function precache(urls) {
  if (!Array.isArray(urls)) return;
  const statics = await caches.open(STATIC);
  for (const raw of urls.slice(0, 300)) {
    try {
      const url = new URL(raw, self.location.origin);
      if (url.origin !== self.location.origin) continue;
      if (isStatic(url)) {
        if (await statics.match(url.href)) continue;
        const res = await fetch(url.href);
        if (res.ok) await statics.put(url.href, res);
      } else {
        const p = url.pathname;
        if (p !== "/app" && !p.startsWith("/app/")) continue;
        const res = await fetch(url.href, { credentials: "same-origin" });
        if (cacheable(url, res)) await storePage(pageKey(url), res);
      }
    } catch {
      /* best effort */
    }
  }
}

/** @brief Cache-first lookup, storing successful network responses. */
async function cacheFirst(req) {
  const cache = await caches.open(STATIC);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone()).catch(() => {});
  return res;
}

/** Auth/one-time-token routes are never stored (and are outside /app anyway). */
const NEVER = [
  "/login",
  "/callback",
  "/sso-test",
  "/reset-password",
  "/magic-link",
  "/register",
  "/two-factor",
];

/** @brief Cache key: pathname only (query allow-list is empty for now). */
function pageKey(url) {
  return url.origin + url.pathname;
}

/** @brief Only plain /app shell HTML responses may be stored. */
function cacheable(url, res) {
  const p = url.pathname;
  if (p !== "/app" && !p.startsWith("/app/")) return false;
  if (NEVER.some((n) => p === n || p.startsWith(n + "/"))) return false;
  // /app HTML is a user-agnostic client-rendered shell (auth + data come from
  // /api, never cached), so Next's no-store on dynamic routes is ignored.
  return res.ok && !res.redirected;
}

/** @brief Store page as most-recent (delete+put) and evict oldest over cap. */
async function storePage(key, res) {
  const cache = await caches.open(PAGES);
  await cache.delete(key);
  await cache.put(key, res);
  const keys = await cache.keys();
  for (const k of keys.slice(0, Math.max(0, keys.length - MAX_PAGES)))
    await cache.delete(k);
}

/** @brief Network-first navigation; falls back to saved page, then /offline. */
async function navigate(event, req) {
  const url = new URL(req.url);
  const key = pageKey(url);
  try {
    const res = await fetch(req);
    if (cacheable(url, res))
      event.waitUntil(storePage(key, res.clone()).catch(() => {}));
    return res;
  } catch {
    const cache = await caches.open(PAGES);
    const cached = await cache.match(key);
    if (cached) {
      event.waitUntil(storePage(key, cached.clone()).catch(() => {}));
      return cached;
    }
    // Miss on an /app route: any cached /app page is the same shell; the
    // client router renders the requested route from it.
    if (url.pathname.startsWith("/app/")) {
      const keys = await cache.keys();
      const shell = keys.length && (await cache.match(keys[keys.length - 1]));
      if (shell) return shell;
    }
    const offline = await caches.match("/offline");
    return offline || Response.error();
  }
}

/** @brief True for Next App Router RSC payload fetches (in-app navigation). */
function isRsc(req, url) {
  return (
    (req.headers && req.headers.get("RSC") === "1") ||
    url.searchParams.has("_rsc")
  );
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/"))
    return;
  if (isStatic(url) || req.destination === "font") {
    event.respondWith(cacheFirst(req));
  } else if (isRsc(req, url)) {
    // RSC payloads are never cached (user data, Vary). Offline they must fail
    // fast: Next's client router treats a failed RSC fetch as an MPA
    // navigation (router-reducer/fetch-server-response), i.e. a hard
    // navigation that the navigate handler then serves from the page cache.
    event.respondWith(fetch(req).catch(() => Response.error()));
  } else if (req.mode === "navigate") {
    event.respondWith(navigate(event, req));
  }
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { title: "Nexara", body: event.data ? event.data.text() : "" };
  }
  const options = {
    body: data.body || "",
    icon: "/icons/icon-192.png",
    badge: "/icons/badge-72.png",
    tag: data.tag || "nexara-notification",
    renotify: true,
    data: { url: data.url || "/app" },
  };
  const jobs = [
    self.registration.showNotification(data.title || "Nexara", options),
  ];
  if (typeof data.badge_count === "number" && self.navigator?.setAppBadge)
    jobs.push(
      Promise.resolve(self.navigator.setAppBadge(data.badge_count)).catch(
        () => {},
      ),
    );
  event.waitUntil(Promise.all(jobs));
});

/** @brief Same-origin path+query+hash of raw, else "/app". The normalised
 *         path must also pass lib safePath's rule: "/.//evil.com" normalises
 *         to "//evil.com", which openWindow would resolve off-origin. */
function safeTarget(raw) {
  try {
    const u = new URL(raw, self.location.origin);
    const out = u.pathname + u.search + u.hash;
    if (u.origin === self.location.origin && /^\/(?![/\\])/.test(out))
      return out;
  } catch {
    /* fall through */
  }
  return "/app";
}

/** @brief Focus the matching visible tab, else focused/visible/any (+navigate msg), else open. */
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = safeTarget(
    event.notification.data && event.notification.data.url,
  );
  const path = target.split(/[?#]/)[0];
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((all) => {
        const match = all.find(
          (c) =>
            c.visibilityState === "visible" &&
            new URL(c.url, self.location.origin).pathname === path,
        );
        const client =
          match ||
          all.find((c) => c.focused) ||
          all.find((c) => c.visibilityState === "visible") ||
          all[0];
        if (client) {
          if (!match) client.postMessage({ type: "navigate", url: target });
          return client.focus();
        }
        return self.clients.openWindow(target);
      }),
  );
});
