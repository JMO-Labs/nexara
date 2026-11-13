/**
 * @file tests/unit/components/notifications/ToastBridge.test.tsx
 * @brief ToastBridge: SSE notification events become toasts.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";
import { useToasts } from "@/stores/toasts";

type Handler = (data: unknown, type: string) => void;
let handler: Handler = () => {};
const sseSpy = vi.fn();
vi.mock("@/hooks/useSSE", () => ({
  useSSE: (path: string, opts: { onMessage: Handler }) => {
    sseSpy(path, opts);
    handler = opts.onMessage;
  },
}));
const dismissOne = vi.fn(() => Promise.resolve({ message: "ok" }));
vi.mock("@/lib/api/notifications", () => ({
  STREAM_PATH: "/api/v1/notifications/stream",
  dismissOne: (id: string) => dismissOne(id),
}));
const desc = (key: string, over = {}) => ({
  key,
  label_i18n: "notifications.title",
  icon: "bell",
  actions: [],
  toast_on_arrival: true,
  bypass_dnd: false,
  ...over,
});
const byKey = new Map([
  ["a", desc("a")],
  ["quiet", desc("quiet", { toast_on_arrival: false })],
  ["urgent", desc("urgent", { bypass_dnd: true })],
]);
vi.mock("@/lib/notifications/registry", () => ({
  useNotificationRegistry: () => ({ byKey }),
}));

import { ToastBridge } from "@/components/notifications/ToastBridge";

const mount = () =>
  render(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      <ToastBridge />
    </NextIntlClientProvider>,
  );

describe("ToastBridge", () => {
  beforeEach(() => {
    useToasts.getState().clear();
    dismissOne.mockClear();
  });

  it("subscribes to the stream with both event types", () => {
    mount();
    expect(sseSpy).toHaveBeenCalledWith(
      "/api/v1/notifications/stream",
      expect.objectContaining({
        eventTypes: ["user_notification", "user_toast"],
      }),
    );
  });

  it("skips types without toast_on_arrival and unknown types", () => {
    mount();
    handler({ type: "quiet", id: "1" }, "user_notification");
    handler({ type: "nope", id: "2" }, "user_notification");
    expect(useToasts.getState().items).toHaveLength(0);
  });

  it("pushes an info toast with rendered title/body", () => {
    mount();
    handler(
      { type: "a", id: "3", payload: { message: "hello" } },
      "user_notification",
    );
    const [t] = useToasts.getState().items;
    expect(t.variant).toBe("info");
    expect(t.title).toBe("Notifications");
    expect(t.message).toBe("hello");
    expect(t.action).toBeUndefined();
  });

  it("uses warning variant for bypass_dnd", () => {
    mount();
    handler({ type: "urgent", id: "4" }, "user_toast");
    expect(useToasts.getState().items[0].variant).toBe("warning");
  });

  it("dedupes repeated events with the same id", () => {
    mount();
    const evt = { type: "a", id: "5" };
    handler(evt, "user_notification");
    handler(evt, "user_notification");
    expect(useToasts.getState().items).toHaveLength(1);
  });

  it("action dismisses and navigates to the link", () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    mount();
    handler(
      { type: "a", id: "6", payload: { link: "/app/x" } },
      "user_notification",
    );
    const { action } = useToasts.getState().items[0];
    expect(action?.label).toBe("Open");
    action?.onClick();
    expect(dismissOne).toHaveBeenCalledWith("6");
    expect(assign).toHaveBeenCalledWith("/app/x");
    vi.unstubAllGlobals();
  });
});
