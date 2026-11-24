/**
 * @file tests/unit/sw.test.ts
 * @brief Loads public/sw.js in a fake `self` and asserts caching behaviour.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const SRC = fs.readFileSync(
  path.resolve(__dirname, "../../public/sw.js"),
  "utf8",
);

type Handler = (e: any) => void;

function makeEnv(opts: { importFails?: boolean } = {}) {
  const stores = new Map<string, Map<string, any>>();
  const open = (name: string) => {
    if (!stores.has(name)) stores.set(name, new Map());
    const m = stores.get(name)!;
    return Promise.resolve({
      match: (r: any) =>
        Promise.resolve(m.get(typeof r === "string" ? r : r.url)),
      put: (r: any, res: any) => {
        m.set(typeof r === "string" ? r : r.url, res);
        return Promise.resolve();
      },
      addAll: () => Promise.resolve(),
      delete: (r: any) =>
        Promise.resolve(m.delete(typeof r === "string" ? r : r.url)),
      keys: () => Promise.resolve([...m.keys()].map((url) => ({ url }))),
    });
  };
  const caches = {
    open,
    keys: () => Promise.resolve([...stores.keys()]),
    delete: (n: string) => Promise.resolve(stores.delete(n)),
    match: async (r: any) => {
      for (const m of stores.values()) {
        const hit = m.get(typeof r === "string" ? r : r.url);
        if (hit) return hit;
      }
    },
  };
  const handlers: Record<string, Handler> = {};
  const self: any = {
    location: { origin: "https://x.test" },
    addEventListener: (t: string, h: Handler) => (handlers[t] = h),
    skipWaiting: vi.fn(),
    clients: { claim: vi.fn(), matchAll: vi.fn(), openWindow: vi.fn() },
    registration: { showNotification: vi.fn() },
    importScripts: (u: string) => {
      if (opts.importFails) throw new Error("missing");
      self.__SW_VERSION__ = "abc123";
    },
  };
  const fetchMock = vi.fn();
  const ctx: any = {
    self,
    importScripts: self.importScripts,
    caches,
    fetch: fetchMock,
    URL,
    Response,
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { self, handlers, stores, fetchMock };
}

async function doFetch(
  env: ReturnType<typeof makeEnv>,
  url: string,
  init: any = {},
) {
  const { headers: h = {}, ...rest } = init;
  const req = {
    url,
    method: "GET",
    mode: "no-cors",
    headers: { get: (k: string) => h[k] ?? null },
    ...rest,
  };
  let p: Promise<any> | undefined;
  const waits: Promise<any>[] = [];
  env.handlers.fetch({
    request: req,
    respondWith: (x: any) => (p = x),
    waitUntil: (x: any) => waits.push(x),
  });
  const out = p === undefined ? undefined : await p;
  await Promise.all(waits);
  return out;
}

describe("sw.js", () => {
  let env: ReturnType<typeof makeEnv>;
  beforeEach(() => {
    env = makeEnv();
  });

  it("versions caches from sw-version.js, 'dev' when missing", async () => {
    const names = async (e: ReturnType<typeof makeEnv>) => {
      const waits: Promise<any>[] = [];
      e.handlers.install({ waitUntil: (x: any) => waits.push(x) });
      await Promise.all(waits);
      return [...e.stores.keys()];
    };
    expect(await names(env)).toEqual(["nexara-abc123"]);
    expect(await names(makeEnv({ importFails: true }))).toEqual(["nexara-dev"]);
  });

  it("does not skipWaiting on install, does on message", () => {
    env.handlers.install({ waitUntil: () => {} });
    expect(env.self.skipWaiting).not.toHaveBeenCalled();
    env.handlers.message({ data: { type: "SKIP_WAITING" } });
    expect(env.self.skipWaiting).toHaveBeenCalledTimes(1);
  });

  it("serves /_next/static cache-first", async () => {
    env.fetchMock.mockResolvedValue(new Response("js"));
    await doFetch(env, "https://x.test/_next/static/a.js");
    expect(env.fetchMock).toHaveBeenCalledTimes(1);
    const res = await doFetch(env, "https://x.test/_next/static/a.js");
    expect(env.fetchMock).toHaveBeenCalledTimes(1);
    expect(await res.text()).toBe("js");
  });

  it("never handles API requests", async () => {
    expect(await doFetch(env, "https://x.test/api/v1/posts")).toBeUndefined();
    expect(env.fetchMock).not.toHaveBeenCalled();
  });

  it("network-first navigations fall back to cache offline, capped at 30", async () => {
    env.fetchMock.mockImplementation(() => Promise.resolve(new Response("pg")));
    for (let i = 0; i < 32; i++)
      await doFetch(env, `https://x.test/app/p${i}`, { mode: "navigate" });
    const pages = [...env.stores.entries()].find(([k]) =>
      k.includes("pages"),
    )![1];
    expect(pages.size).toBe(30);
    expect(pages.has("https://x.test/app/p0")).toBe(false);
    env.fetchMock.mockRejectedValue(new Error("offline"));
    const res = await doFetch(env, "https://x.test/app/p31", {
      mode: "navigate",
    });
    expect(await res.text()).toBe("pg");
  });

  const pages = (e: ReturnType<typeof makeEnv>) =>
    [...e.stores.entries()].find(([k]) => k.includes("pages"))?.[1];

  it("RSC requests fail fast offline and are never cached", async () => {
    env.fetchMock.mockResolvedValueOnce(new Response("flight"));
    await doFetch(env, "https://x.test/app/chat?_rsc=abc", {
      headers: { RSC: "1" },
      mode: "cors",
    });
    expect(pages(env)).toBeUndefined();
    env.fetchMock.mockRejectedValue(new Error("offline"));
    const res = await doFetch(env, "https://x.test/app/chat?_rsc=abc", {
      headers: { RSC: "1" },
      mode: "cors",
    });
    expect(res.type).toBe("error");
  });

  it("keys pages by pathname only", async () => {
    env.fetchMock.mockResolvedValue(new Response("pg"));
    await doFetch(env, "https://x.test/app/chat?token=1", { mode: "navigate" });
    expect([...pages(env)!.keys()]).toEqual(["https://x.test/app/chat"]);
  });

  it.each([
    ["/login"],
    ["/callback"],
    ["/sso-test"],
    ["/reset-password"],
    ["/magic-link"],
    ["/register"],
    ["/two-factor"],
    ["/other"],
  ])("never caches %s", async (p) => {
    env.fetchMock.mockResolvedValue(new Response("x"));
    await doFetch(env, "https://x.test" + p, { mode: "navigate" });
    expect(pages(env)).toBeUndefined();
  });

  it("caches /app/events/123 despite no-store (client-rendered shell)", async () => {
    env.fetchMock.mockResolvedValue(
      new Response("shell", {
        headers: { "Cache-Control": "private, no-store" },
      }),
    );
    await doFetch(env, "https://x.test/app/events/123", { mode: "navigate" });
    expect([...pages(env)!.keys()]).toEqual(["https://x.test/app/events/123"]);
  });

  it("skips non-ok and redirected responses", async () => {
    const redirected = new Response("d");
    Object.defineProperty(redirected, "redirected", { value: true });
    for (const r of [new Response("c", { status: 500 }), redirected]) {
      env.fetchMock.mockResolvedValueOnce(r);
      await doFetch(env, "https://x.test/app/x", { mode: "navigate" });
    }
    expect(pages(env)).toBeUndefined();
  });

  it("offline miss on /app/** serves a cached /app shell", async () => {
    env.fetchMock.mockResolvedValueOnce(new Response("shell"));
    await doFetch(env, "https://x.test/app", { mode: "navigate" });
    env.fetchMock.mockRejectedValue(new Error("offline"));
    const res = await doFetch(env, "https://x.test/app/events/999", {
      mode: "navigate",
    });
    expect(await res.text()).toBe("shell");
  });

  it("CLEAR_USER_CACHE deletes the pages cache", async () => {
    env.fetchMock.mockResolvedValue(new Response("pg"));
    await doFetch(env, "https://x.test/app/a", { mode: "navigate" });
    expect(pages(env)).toBeDefined();
    const waits: Promise<any>[] = [];
    env.handlers.message({
      data: { type: "CLEAR_USER_CACHE" },
      waitUntil: (x: any) => waits.push(x),
    });
    await Promise.all(waits);
    expect(pages(env)).toBeUndefined();
  });

  describe("push", () => {
    const push = (d: any) => {
      const waits: Promise<any>[] = [];
      env.handlers.push({
        data: { json: () => d, text: () => "" },
        waitUntil: (x: any) => waits.push(x),
      });
      return Promise.all(waits);
    };
    it("shows a stacked notification and sets the badge", async () => {
      const setAppBadge = vi.fn().mockResolvedValue(undefined);
      env.self.navigator = { setAppBadge };
      await push({
        title: "T",
        body: "B",
        url: "/app/x",
        tag: "g",
        badge_count: 4,
      });
      expect(env.self.registration.showNotification).toHaveBeenCalledWith(
        "T",
        expect.objectContaining({
          body: "B",
          tag: "g",
          renotify: true,
          badge: "/icons/badge-72.png",
          data: { url: "/app/x" },
        }),
      );
      expect(setAppBadge).toHaveBeenCalledWith(4);
    });
    it("works without setAppBadge", async () => {
      await push({ title: "T", badge_count: 2 });
      expect(env.self.registration.showNotification).toHaveBeenCalledTimes(1);
    });
  });

  describe("notificationclick", () => {
    const click = async (clients: any[], url = "/app/events") => {
      env.self.clients.matchAll.mockResolvedValue(clients);
      const close = vi.fn();
      const waits: Promise<any>[] = [];
      env.handlers.notificationclick({
        notification: { close, data: { url } },
        waitUntil: (x: any) => waits.push(x),
      });
      await Promise.all(waits);
      expect(close).toHaveBeenCalled();
    };
    const mk = (url: string, vis: string) => ({
      url,
      visibilityState: vis,
      focus: vi.fn().mockResolvedValue(undefined),
      postMessage: vi.fn(),
    });
    it("focuses a visible client already on the URL", async () => {
      const a = mk("https://x.test/app/chat", "visible");
      const b = mk("https://x.test/app/events", "visible");
      await click([a, b]);
      expect(b.focus).toHaveBeenCalled();
      expect(b.postMessage).not.toHaveBeenCalled();
      expect(a.focus).not.toHaveBeenCalled();
    });
    it("posts navigate to another client otherwise", async () => {
      const a = mk("https://x.test/app/chat", "hidden");
      await click([a]);
      expect(a.postMessage).toHaveBeenCalledWith({
        type: "navigate",
        url: "/app/events",
      });
      expect(a.focus).toHaveBeenCalled();
    });
    it.each([
      ["https://evil.com/x"],
      ["//evil.com"],
      ["/\\evil.com"],
      ["javascript:alert(1)"],
    ])("never opens or navigates to %s", async (bad) => {
      const a = mk("https://x.test/app/chat", "hidden");
      await click([a], bad);
      const sent = a.postMessage.mock.calls[0]?.[0].url;
      expect(sent).toMatch(/^\/(?![/\\])/);
      await click([], bad);
      expect(env.self.clients.openWindow.mock.calls.at(-1)![0]).toMatch(
        /^\/(?![/\\])/,
      );
    });
    it("prefers focused, then visible client for fallback", async () => {
      const a = mk("https://x.test/app/a", "hidden");
      const b = mk("https://x.test/app/b", "visible");
      const c = { ...mk("https://x.test/app/c", "hidden"), focused: true };
      await click([a, b, c]);
      expect(c.postMessage).toHaveBeenCalled();
      expect(b.postMessage).not.toHaveBeenCalled();
      c.focused = false;
      await click([a, b]);
      expect(b.postMessage).toHaveBeenCalled();
    });
    it("opens a window when none exist", async () => {
      await click([]);
      expect(env.self.clients.openWindow).toHaveBeenCalledWith("/app/events");
    });
  });
});
