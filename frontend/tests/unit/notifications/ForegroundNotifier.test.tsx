/**
 * @file tests/unit/notifications/ForegroundNotifier.test.tsx
 * @brief Hidden tab + no push -> OS notification; otherwise silent.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";

const m = vi.hoisted(() => ({
  onMessage: null as null | ((d: unknown) => Promise<void>),
  subscribed: false,
  loading: false,
}));
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/hooks/useSSE", () => ({
  useSSE: (_p: string, o: { onMessage: (d: unknown) => Promise<void> }) => {
    m.onMessage = o.onMessage;
  },
}));
vi.mock("@/hooks/usePushNotifications", () => ({
  usePushNotifications: () => ({
    isSubscribed: m.subscribed,
    isLoading: m.loading,
  }),
}));
vi.mock("@/lib/api/notifications", () => ({ STREAM_PATH: "/s" }));
vi.mock("@/lib/notifications/registry", () => ({
  useNotificationRegistry: () => ({
    byKey: new Map([["mention", { key: "mention" }]]),
  }),
}));
vi.mock("@/lib/notifications/renderers", () => ({
  renderNotif: () => ({ title: "Hi", body: "B", link: "/app/x" }),
}));

import { ForegroundNotifier } from "@/components/notifications/ForegroundNotifier";

const show = vi.fn().mockResolvedValue(undefined);
const evt = { type: "mention", id: "1", payload: {} };

function setup(visibility: string, perm = "granted") {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => visibility,
  });
  vi.stubGlobal("Notification", { permission: perm });
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: { ready: Promise.resolve({ showNotification: show }) },
  });
  render(<ForegroundNotifier />);
}

describe("ForegroundNotifier", () => {
  beforeEach(() => {
    show.mockClear();
    m.subscribed = false;
    m.loading = false;
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows one notification with tag when hidden and no push", async () => {
    setup("hidden");
    await m.onMessage!(evt);
    expect(show).toHaveBeenCalledTimes(1);
    expect(show).toHaveBeenCalledWith(
      "Hi",
      expect.objectContaining({ tag: "mention", data: { url: "/app/x" } }),
    );
  });

  it("is silent when the tab is visible", async () => {
    setup("visible");
    await m.onMessage!(evt);
    expect(show).not.toHaveBeenCalled();
  });

  it("is silent when this device has push", async () => {
    m.subscribed = true;
    setup("hidden");
    await m.onMessage!(evt);
    expect(show).not.toHaveBeenCalled();
  });

  it("is silent while devices are loading", async () => {
    m.loading = true;
    setup("hidden");
    await m.onMessage!(evt);
    expect(show).not.toHaveBeenCalled();
  });

  it("tags with type:thread like the backend", async () => {
    setup("hidden");
    await m.onMessage!({ ...evt, payload: { post_id: "p9" } });
    expect(show).toHaveBeenCalledWith(
      "Hi",
      expect.objectContaining({ tag: "mention:p9" }),
    );
  });

  it("is silent without permission", async () => {
    setup("hidden", "default");
    await m.onMessage!(evt);
    expect(show).not.toHaveBeenCalled();
  });
});
