/**
 * @file tests/unit/auth/session-offline.test.ts
 * @brief Network errors during refresh or /users/me never end the session;
 *        only a 401/403 answer does. Logout drops this device's push sub.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { api } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import {
  getAccessToken,
  logout,
  refreshSession,
  setAccessToken,
} from "@/lib/auth/session";
import { saveLastUser } from "@/lib/auth/lastUser";
import { useSessionBootstrap } from "@/hooks/useSession";
import { useSession } from "@/stores/session";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
const offline = (): Promise<Response> =>
  Promise.reject(new TypeError("Failed to fetch"));
const ME = { id: "u1", display_name: "A" } as never;
const postMessage = vi.fn();

beforeEach(() => {
  Object.defineProperty(navigator, "serviceWorker", {
    value: { controller: { postMessage } },
    configurable: true,
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  postMessage.mockClear();
  setAccessToken(null);
  localStorage.clear();
  useSession.setState({ user: null, status: "idle" });
  delete (navigator as any).serviceWorker;
});

describe("refreshSession", () => {
  it("keeps the token on a network error", async () => {
    setAccessToken("old");
    vi.stubGlobal("fetch", vi.fn(offline));
    expect(await refreshSession()).toEqual({ token: null, transient: true });
    expect(getAccessToken()).toBe("old");
  });

  it("keeps the token on a 5xx", async () => {
    setAccessToken("old");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, 502)));
    expect((await refreshSession()).transient).toBe(true);
    expect(getAccessToken()).toBe("old");
  });

  it("clears the token on 401", async () => {
    setAccessToken("old");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, 401)));
    expect(await refreshSession()).toEqual({ token: null, transient: false });
    expect(getAccessToken()).toBeNull();
  });
});

describe("api() 401 + refresh", () => {
  it("network error during refresh: throws, keeps session, no expiry event", async () => {
    setAccessToken("old");
    const expired = vi.fn();
    window.addEventListener("nx:auth-expired", expired);
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        url.endsWith("/auth/refresh")
          ? offline()
          : Promise.resolve(json({}, 401)),
      ),
    );
    const err = (await api("/api/v1/x").catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(getAccessToken()).toBe("old");
    expect(expired).not.toHaveBeenCalled();
    window.removeEventListener("nx:auth-expired", expired);
  });

  it("refresh 401: clears session and signals expiry", async () => {
    setAccessToken("old");
    const expired = vi.fn();
    window.addEventListener("nx:auth-expired", expired);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, 401)));
    await expect(api("/api/v1/x")).rejects.toBeInstanceOf(ApiError);
    expect(getAccessToken()).toBeNull();
    expect(expired).toHaveBeenCalled();
    window.removeEventListener("nx:auth-expired", expired);
  });
});

describe("session bootstrap", () => {
  it("offline cold load boots the last user without purging", async () => {
    saveLastUser(ME);
    vi.stubGlobal("fetch", vi.fn(offline));
    renderHook(() => useSessionBootstrap());
    await waitFor(() =>
      expect(useSession.getState().status).toBe("authenticated"),
    );
    expect(useSession.getState().user).toMatchObject(ME);
    expect(postMessage).not.toHaveBeenCalled();
  });

  it("/users/me network error keeps the session", async () => {
    saveLastUser(ME);
    setAccessToken("tok");
    vi.stubGlobal("fetch", vi.fn(offline));
    renderHook(() => useSessionBootstrap());
    await waitFor(() =>
      expect(useSession.getState().status).toBe("authenticated"),
    );
    expect(getAccessToken()).toBe("tok");
  });

  it("offline with no last user waits, then retries when online", async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(offline);
    vi.stubGlobal("fetch", fetchMock);
    renderHook(() => useSessionBootstrap());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(useSession.getState().status).toBe("loading");
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url.endsWith("/auth/refresh") ? json({ access_token: "n" }) : json(ME),
      ),
    );
    window.dispatchEvent(new Event("online"));
    await waitFor(() =>
      expect(useSession.getState().status).toBe("authenticated"),
    );
  });

  it("server 5xx while online: retries with backoff, no snapshot", async () => {
    vi.useFakeTimers();
    try {
      const fetchMock = vi.fn<(url: string) => Promise<Response>>(() =>
        Promise.resolve(json({}, 503)),
      );
      vi.stubGlobal("fetch", fetchMock);
      renderHook(() => useSessionBootstrap());
      await vi.advanceTimersByTimeAsync(0);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(2_000);
      expect(fetchMock).toHaveBeenCalledTimes(2);
      fetchMock.mockImplementation((url: string) =>
        Promise.resolve(
          url.endsWith("/auth/refresh")
            ? json({ access_token: "n" })
            : json(ME),
        ),
      );
      await vi.advanceTimersByTimeAsync(5_000);
      expect(useSession.getState().status).toBe("authenticated");
    } finally {
      vi.useRealTimers();
    }
  });

  it("retries when the app becomes visible again", async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(() =>
      Promise.resolve(json({}, 429)),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderHook(() => useSessionBootstrap());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url.endsWith("/auth/refresh") ? json({ access_token: "n" }) : json(ME),
      ),
    );
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await waitFor(() =>
      expect(useSession.getState().status).toBe("authenticated"),
    );
  });

  it("booting from the snapshot does not extend its lifetime", async () => {
    vi.spyOn(Date, "now").mockReturnValue(1_000);
    saveLastUser(ME);
    vi.spyOn(Date, "now").mockReturnValue(5_000);
    vi.stubGlobal("fetch", vi.fn(offline));
    renderHook(() => useSessionBootstrap());
    await waitFor(() =>
      expect(useSession.getState().status).toBe("authenticated"),
    );
    expect(JSON.parse(localStorage.getItem("nx_last_user")!).at).toBe(1_000);
    vi.restoreAllMocks();
  });

  it("refresh 401 signs out and forgets the last user", async () => {
    saveLastUser(ME);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, 401)));
    renderHook(() => useSessionBootstrap());
    await waitFor(() =>
      expect(useSession.getState().status).toBe("unauthenticated"),
    );
    expect(localStorage.getItem("nx_last_user")).toBeNull();
  });
});

describe("logout", () => {
  it("unregisters this device's push subscription first", async () => {
    setAccessToken("tok");
    const unsubscribe = vi.fn().mockResolvedValue(true);
    const sub = { endpoint: "https://push.example/e1", unsubscribe };
    (navigator as any).serviceWorker.getRegistration = () =>
      Promise.resolve({
        pushManager: { getSubscription: () => Promise.resolve(sub) },
      });
    const fetchMock = vi.fn().mockResolvedValue(json({ message: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    await logout();
    const del = fetchMock.mock.calls.find(
      ([u, i]) => u.endsWith("/api/v1/push/subscribe") && i.method === "DELETE",
    );
    expect(JSON.parse(del![1].body)).toEqual({ endpoint: sub.endpoint });
    expect((del![1].headers as Headers).get("Authorization")).toBe(
      "Bearer tok",
    );
    expect(unsubscribe).toHaveBeenCalled();
    expect(getAccessToken()).toBeNull();
  });
});

describe("last-user snapshot", () => {
  it("stores only shell fields", () => {
    saveLastUser({
      id: "u1",
      username: "a",
      display_name: "A",
      avatar_url: null,
      role: "member",
      is_active: true,
      tour_completed_at: null,
      timezone: "UTC",
      email: "a@b.c",
      phone: "123",
      contact_email: "c@d.e",
      address: "1 Road",
      birthday: "2000-01-01",
      emergency_contact: { name: "M", phone: "9", relation: "mum" },
      dietary: "vegan",
      bio: "hi",
    });
    const raw = localStorage.getItem("nx_last_user")!;
    for (const bad of [
      "a@b.c",
      "123",
      "c@d.e",
      "1 Road",
      "2000-01-01",
      "emergency",
      "vegan",
      "bio",
    ])
      expect(raw).not.toContain(bad);
    expect(JSON.parse(raw).user).toEqual({
      id: "u1",
      username: "a",
      display_name: "A",
      avatar_url: null,
      role: "member",
      is_active: true,
      tour_completed_at: null,
      timezone: "UTC",
    });
  });
});
