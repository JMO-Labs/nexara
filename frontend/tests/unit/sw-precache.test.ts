/**
 * @file tests/unit/sw-precache.test.ts
 * @brief sw.js CACHE_URLS (first-visit offline caching) and the sign-out
 *        purge of notifications and app badge.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { makeEnv } from "./swEnv";

type Env = ReturnType<typeof makeEnv>;

async function message(env: Env, data: unknown) {
  const waits: Promise<unknown>[] = [];
  env.handlers.message({ data, waitUntil: (x: any) => waits.push(x) });
  await Promise.all(waits);
}

const store = (env: Env, suffix: string) =>
  [...env.stores.entries()].find(([k]) => k.endsWith(suffix))?.[1];

describe("sw.js CACHE_URLS", () => {
  let env: Env;
  beforeEach(() => {
    env = makeEnv();
    env.fetchMock.mockImplementation(() => Promise.resolve(new Response("x")));
  });

  it("claims clients on activate", async () => {
    const waits: Promise<unknown>[] = [];
    env.handlers.activate({ waitUntil: (x: any) => waits.push(x) });
    await Promise.all(waits);
    expect(env.self.clients.claim).toHaveBeenCalled();
  });

  it("caches static assets and the /app page into their caches", async () => {
    await message(env, {
      type: "CACHE_URLS",
      urls: [
        "/app/events?x=1",
        "/_next/static/chunks/a.js",
        "/_next/static/media/f.woff2",
      ],
    });
    expect([...store(env, "-static")!.keys()]).toEqual([
      "https://x.test/_next/static/chunks/a.js",
      "https://x.test/_next/static/media/f.woff2",
    ]);
    expect([...store(env, "-pages")!.keys()]).toEqual([
      "https://x.test/app/events",
    ]);
  });

  it("ignores other origins, non-/app pages and auth pages", async () => {
    await message(env, {
      type: "CACHE_URLS",
      urls: [
        "https://evil.com/_next/static/a.js",
        "/login",
        "/register",
        "/",
        "/api/v1/users/me",
      ],
    });
    expect(env.fetchMock).not.toHaveBeenCalled();
    expect(store(env, "-pages")).toBeUndefined();
  });

  it("skips statics already cached and failed responses", async () => {
    await message(env, { type: "CACHE_URLS", urls: ["/_next/static/a.js"] });
    await message(env, { type: "CACHE_URLS", urls: ["/_next/static/a.js"] });
    expect(env.fetchMock).toHaveBeenCalledTimes(1);
    env.fetchMock.mockResolvedValue(new Response("no", { status: 500 }));
    await message(env, { type: "CACHE_URLS", urls: ["/app"] });
    expect(store(env, "-pages")?.size ?? 0).toBe(0);
  });

  it("survives a malformed payload", async () => {
    await expect(
      message(env, { type: "CACHE_URLS", urls: "nope" }),
    ).resolves.toBeUndefined();
  });
});

describe("sw.js CLEAR_USER_CACHE", () => {
  it("closes shown notifications and clears the app badge", async () => {
    const env = makeEnv();
    const close = vi.fn();
    env.self.registration.getNotifications.mockResolvedValue([
      { close },
      { close },
    ]);
    const clearAppBadge = vi.fn().mockResolvedValue(undefined);
    env.self.navigator = { clearAppBadge };
    await message(env, { type: "CLEAR_USER_CACHE" });
    expect(close).toHaveBeenCalledTimes(2);
    expect(clearAppBadge).toHaveBeenCalled();
  });
});
