/**
 * @file tests/unit/swEnv.ts
 * @brief Test harness: runs public/sw.js in a fake `self` with fake caches.
 */
import { vi } from "vitest";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const SRC = fs.readFileSync(
  path.resolve(__dirname, "../../public/sw.js"),
  "utf8",
);

type Handler = (e: any) => void;

export function makeEnv(opts: { importFails?: boolean } = {}) {
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
    registration: { showNotification: vi.fn(), getNotifications: vi.fn() },
    importScripts: () => {
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

export async function doFetch(
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
