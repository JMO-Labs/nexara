/**
 * @file tests/unit/hooks/usePushNotifications.test.ts
 * @brief usePushNotifications: unsupported browser, denied, subscribe.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, waitFor } from "@testing-library/react";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

const api = vi.hoisted(() => ({
  getVapidKey: vi.fn(),
  listPushSubscriptions: vi.fn(),
  subscribePush: vi.fn(),
  unsubscribePush: vi.fn(),
}));
vi.mock("@/lib/api/push", () => api);
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));

const sub = {
  endpoint: "https://push.example/1",
  toJSON: () => ({
    endpoint: "https://push.example/1",
    keys: { p256dh: "pk", auth: "ak" },
  }),
  getKey: () => null,
  unsubscribe: vi.fn(),
};

function setupBrowser(
  permission: NotificationPermission,
  requested?: NotificationPermission,
) {
  const pushManager = {
    getSubscription: vi.fn().mockResolvedValue(null),
    subscribe: vi.fn().mockResolvedValue(sub),
  };
  vi.stubGlobal("Notification", {
    permission,
    requestPermission: vi.fn().mockResolvedValue(requested ?? permission),
  });
  vi.stubGlobal("PushManager", class {});
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: { ready: Promise.resolve({ pushManager }) },
  });
  return pushManager;
}

describe("usePushNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listPushSubscriptions.mockResolvedValue([]);
    api.getVapidKey.mockResolvedValue({ public_key: "AQAB" });
    api.subscribePush.mockResolvedValue({ id: "1" });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (navigator as any).serviceWorker;
  });

  it("reports unsupported when serviceWorker/PushManager are missing", async () => {
    vi.stubGlobal("PushManager", undefined);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).PushManager;
    const { result } = renderHookWithProviders(() => usePushNotifications());
    await waitFor(() => expect(result.current.permission).toBe("unsupported"));
    expect(result.current.supported).toBe(false);
    expect(result.current.isSubscribed).toBe(false);
    await act(async () => {
      await expect(result.current.subscribe()).rejects.toThrow("not supported");
    });
  });

  it("rejects when permission is denied", async () => {
    const pm = setupBrowser("denied");
    const { result } = renderHookWithProviders(() => usePushNotifications());
    await waitFor(() => expect(result.current.permission).toBe("denied"));
    await act(async () => {
      await expect(result.current.subscribe()).rejects.toThrow(
        "Permission denied",
      );
    });
    expect(pm.subscribe).not.toHaveBeenCalled();
    expect(api.subscribePush).not.toHaveBeenCalled();
  });

  it("rejects when the user declines the prompt", async () => {
    setupBrowser("default", "denied");
    const { result } = renderHookWithProviders(() => usePushNotifications());
    await act(async () => {
      await expect(result.current.subscribe()).rejects.toThrow(
        "Permission denied",
      );
    });
    expect(result.current.permission).toBe("denied");
  });

  it("subscribes and posts the subscription to the backend", async () => {
    const pm = setupBrowser("default", "granted");
    const { result } = renderHookWithProviders(() => usePushNotifications());
    await waitFor(() => expect(result.current.supported).toBe(true));
    await act(async () => {
      await result.current.subscribe();
    });
    expect(pm.subscribe).toHaveBeenCalledWith(
      expect.objectContaining({ userVisibleOnly: true }),
    );
    expect(api.subscribePush).toHaveBeenCalledWith({
      endpoint: "https://push.example/1",
      keys: { p256dh: "pk", auth: "ak" },
    });
    expect(result.current.permission).toBe("granted");
  });
});
