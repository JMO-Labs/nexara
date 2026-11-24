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
  const req = { url, method: "GET", mode: "no-cors", ...init };
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
});
