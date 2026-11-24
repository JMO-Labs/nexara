/**
 * @file tests/unit/pwa/precache.test.ts
 * @brief CACHE_URLS poster: current page + same-origin static/font resources,
 *        posted once a controller exists (ready or first controllerchange).
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { collectCacheUrls, startPrecache } from "@/lib/pwa/precache";

type Listener = () => void;

function fakeSw(controller: unknown) {
  const listeners: Listener[] = [];
  const sw = {
    controller,
    ready: Promise.resolve({}),
    addEventListener: (_t: string, l: Listener) => listeners.push(l),
    removeEventListener: vi.fn(),
  };
  Object.defineProperty(navigator, "serviceWorker", {
    value: sw,
    configurable: true,
  });
  return { sw, fire: () => listeners.forEach((l) => l()) };
}

describe("precache poster", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    delete (navigator as any).serviceWorker;
    window.history.replaceState(null, "", "/");
  });

  it("collects the page and same-origin static/font resources", () => {
    window.history.replaceState(null, "", "/app/events?d=1");
    const o = location.origin;
    vi.spyOn(performance, "getEntriesByType").mockReturnValue([
      { name: `${o}/_next/static/chunks/a.js` },
      { name: `${o}/_next/static/chunks/a.js` },
      { name: `${o}/fonts/x.woff2` },
      { name: `${o}/api/v1/users/me` },
      { name: "https://cdn.other/_next/static/b.js" },
    ] as PerformanceEntry[]);
    expect(collectCacheUrls()).toEqual([
      "/app/events?d=1",
      "/_next/static/chunks/a.js",
      "/fonts/x.woff2",
    ]);
  });

  it("posts once when ready with a controller", async () => {
    const postMessage = vi.fn();
    const { fire } = fakeSw({ postMessage });
    startPrecache();
    await Promise.resolve();
    await Promise.resolve();
    fire();
    expect(postMessage).toHaveBeenCalledTimes(1);
    expect(postMessage.mock.calls[0][0].type).toBe("CACHE_URLS");
  });

  it("waits for the first controllerchange when not yet controlled", async () => {
    const postMessage = vi.fn();
    const { sw, fire } = fakeSw(null);
    startPrecache();
    await Promise.resolve();
    expect(postMessage).not.toHaveBeenCalled();
    sw.controller = { postMessage };
    fire();
    expect(postMessage).toHaveBeenCalledTimes(1);
  });

  it("is a no-op without service workers", () => {
    expect(() => startPrecache()()).not.toThrow();
  });
});
