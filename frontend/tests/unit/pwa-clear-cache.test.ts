/**
 * @file tests/unit/pwa-clear-cache.test.ts
 * @brief Pages cache purge on sign-out, login and account switch.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { clearUserCache } from "@/lib/pwa/clearUserCache";
import { useSession } from "@/stores/session";

const postMessage = vi.fn();
function controller(on: boolean) {
  Object.defineProperty(navigator, "serviceWorker", {
    value: { controller: on ? { postMessage } : null },
    configurable: true,
  });
}

describe("clearUserCache", () => {
  afterEach(() => {
    postMessage.mockClear();
    vi.unstubAllGlobals();
    delete (navigator as any).serviceWorker;
    useSession.setState({ user: null, status: "idle" });
  });

  it("posts CLEAR_USER_CACHE to the controller", () => {
    controller(true);
    clearUserCache();
    expect(postMessage).toHaveBeenCalledWith({ type: "CLEAR_USER_CACHE" });
  });

  it("deletes *-pages caches directly without a controller", async () => {
    controller(false);
    const del = vi.fn().mockResolvedValue(true);
    vi.stubGlobal("caches", {
      keys: () => Promise.resolve(["nexara-x-pages", "nexara-x-static"]),
      delete: del,
    });
    clearUserCache();
    await vi.waitFor(() => expect(del).toHaveBeenCalledWith("nexara-x-pages"));
    expect(del).not.toHaveBeenCalledWith("nexara-x-static");
  });

  it("clears the app badge itself without a controller", () => {
    const clearAppBadge = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "serviceWorker", {
      value: { controller: null },
      configurable: true,
    });
    (navigator as any).clearAppBadge = clearAppBadge;
    clearUserCache();
    expect(clearAppBadge).toHaveBeenCalled();
    delete (navigator as any).clearAppBadge;
  });

  it("forgets the last-user snapshot", () => {
    controller(true);
    localStorage.setItem("nx_last_user", "{}");
    clearUserCache();
    expect(localStorage.getItem("nx_last_user")).toBeNull();
  });

  it("session reset (sign-out) and setUser(null) purge", () => {
    controller(true);
    useSession.setState({ user: { id: "a" } as never });
    useSession.getState().reset();
    expect(postMessage).toHaveBeenCalledTimes(1);
    useSession.setState({ user: { id: "a" } as never });
    useSession.getState().setUser(null);
    expect(postMessage).toHaveBeenCalledTimes(2);
  });

  it("account switch purges; same-user update does not", () => {
    controller(true);
    useSession.setState({ user: { id: "a" } as never });
    useSession.getState().setUser({ id: "a", x: 1 } as never);
    expect(postMessage).not.toHaveBeenCalled();
    useSession.getState().setUser({ id: "b" } as never);
    expect(postMessage).toHaveBeenCalledTimes(1);
  });
});
