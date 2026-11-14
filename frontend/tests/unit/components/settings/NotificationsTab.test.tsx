/**
 * @file tests/unit/components/settings/NotificationsTab.test.tsx
 * @brief NotificationsTab: matrix, debounce, snooze, cadence, webhooks.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import en from "@/i18n/en-US.json";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) =>
    (en.settings.notif as Record<string, string>)[k] ?? k,
}));
const sse = vi.hoisted(() => ({ useSSE: vi.fn() }));
vi.mock("@/hooks/useSSE", () => sse);
vi.mock("@/components/settings/PushSubscriptionRow", () => ({
  PushSubscriptionRow: () => <div>push-row</div>,
}));

const api = vi.hoisted(() => ({
  listTypes: vi.fn(),
  getPreferences: vi.fn(),
  patchPreferences: vi.fn(),
  snooze: vi.fn(),
  clearSnooze: vi.fn(),
  listWebhooks: vi.fn(),
  createWebhook: vi.fn(),
  updateWebhook: vi.fn(),
  deleteWebhook: vi.fn(),
}));
vi.mock("@/lib/api/notifications", async (o) => ({
  ...(await o<object>()),
  listTypes: api.listTypes,
  getPreferences: api.getPreferences,
  patchPreferences: api.patchPreferences,
  snooze: api.snooze,
  clearSnooze: api.clearSnooze,
}));
vi.mock("@/lib/api/webhooks", async (o) => ({
  ...(await o<object>()),
  listWebhooks: api.listWebhooks,
  createWebhook: api.createWebhook,
  updateWebhook: api.updateWebhook,
  deleteWebhook: api.deleteWebhook,
}));

import { NotificationsTab } from "@/components/settings/NotificationsTab";

const desc = (key: string, category: string, extra = {}) => ({
  key,
  category,
  default_channels: {},
  user_configurable: ["inapp", "email"],
  digestable: false,
  label_i18n: key,
  ...extra,
});
const TYPES = [
  desc("mention", "social"),
  desc("event_reminder", "event", {
    user_configurable: ["inapp", "push", "toast"],
    digestable: true,
  }),
];
const PREFS = {
  notification_prefs: { mention: { inapp: true, email: false } },
  dnd_schedule: null,
  dnd_until: null,
  dnd_timezone: "UTC",
  digest_cadence: {},
};
const HOOK = {
  id: "w1",
  url: "https://example.com/hook",
  type_keys: ["mention"],
  enabled: true,
  failure_count: 0,
  last_failure_at: null,
  created_at: "",
};

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={qc}>
      <NotificationsTab />
    </QueryClientProvider>,
  );
  return Object.assign(view, { qc });
}

Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.scrollIntoView ??= () => {};

describe("NotificationsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listTypes.mockResolvedValue(TYPES);
    api.getPreferences.mockResolvedValue(PREFS);
    api.patchPreferences.mockResolvedValue(PREFS);
    api.listWebhooks.mockResolvedValue([HOOK]);
    api.snooze.mockResolvedValue({ message: "ok" });
    api.clearSnooze.mockResolvedValue({ message: "ok" });
  });

  it("syncs prefs across tabs via SSE invalidation", async () => {
    const { qc } = renderTab();
    await screen.findByRole("switch", { name: "mention In-app" });
    const opts = sse.useSSE.mock.calls.at(-1)![1];
    expect(opts.eventTypes).toEqual(["user_preferences_updated"]);
    const spy = vi.spyOn(qc, "invalidateQueries");
    opts.onMessage({}, "user_preferences_updated");
    expect(spy).toHaveBeenCalledWith({
      queryKey: ["notifications", "preferences"],
    });
  });

  it("renders only user_configurable channels grouped by category", async () => {
    renderTab();
    expect(
      await screen.findByRole("switch", { name: "mention In-app" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "mention Email" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("switch", { name: "mention Push" })).toBeNull();
    expect(
      screen.getByRole("switch", { name: "event_reminder Push" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "event_reminder Toast" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "social" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "event" })).toBeInTheDocument();
  });

  it("shows cadence select only for digestable types", async () => {
    renderTab();
    await screen.findByRole("switch", { name: "mention Email" });
    expect(
      screen.getByRole("combobox", { name: "event_reminder Digest" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("combobox", { name: "mention Digest" }),
    ).toBeNull();
  });

  it("debounces toggles into one patch", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(
      await screen.findByRole("switch", { name: "mention Email" }),
    );
    await user.click(screen.getByRole("switch", { name: "mention In-app" }));
    expect(api.patchPreferences).not.toHaveBeenCalled();
    await waitFor(() => expect(api.patchPreferences).toHaveBeenCalledTimes(1));
    expect(api.patchPreferences).toHaveBeenCalledWith({
      notification_prefs: { mention: { inapp: false, email: true } },
    });
  });

  it("debounces a cadence change into one patch", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(
      await screen.findByRole("combobox", { name: "event_reminder Digest" }),
    );
    await user.click(await screen.findByRole("option", { name: "Daily" }));
    expect(api.patchPreferences).not.toHaveBeenCalled();
    await waitFor(() => expect(api.patchPreferences).toHaveBeenCalledTimes(1));
    expect(api.patchPreferences).toHaveBeenCalledWith({
      digest_cadence: { event_reminder: "daily" },
    });
  });

  it("debounces a quiet-hours change into one patch", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(
      await screen.findByRole("button", { name: "Add window Mon" }),
    );
    expect(api.patchPreferences).not.toHaveBeenCalled();
    await waitFor(() => expect(api.patchPreferences).toHaveBeenCalledTimes(1));
    expect(api.patchPreferences).toHaveBeenCalledWith({
      dnd_schedule: { mon: [{ start: "22:00", end: "07:00" }] },
      dnd_timezone: "UTC",
    });
  });

  it("flushes pending changes on unmount", async () => {
    const user = userEvent.setup();
    const { unmount } = renderTab();
    await user.click(
      await screen.findByRole("switch", { name: "mention Email" }),
    );
    unmount();
    expect(api.patchPreferences).toHaveBeenCalledTimes(1);
    expect(api.patchPreferences).toHaveBeenCalledWith({
      notification_prefs: { mention: { inapp: true, email: true } },
    });
  });

  it("snoozes for one hour and clears", async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(await screen.findByRole("button", { name: "1 hour" }));
    expect(api.snooze).toHaveBeenCalledWith("1h");
    await user.click(screen.getByRole("button", { name: "Until morning" }));
    expect(api.snooze).toHaveBeenCalledWith("until_morning");
    await user.click(screen.getByRole("button", { name: "Until tomorrow" }));
    expect(api.snooze).toHaveBeenLastCalledWith(
      expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/),
    );
  });

  it("shows Clear only when snoozed", async () => {
    api.getPreferences.mockResolvedValue({
      ...PREFS,
      dnd_until: "2030-01-01T00:00:00Z",
    });
    renderTab();
    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Clear" }));
    expect(api.clearSnooze).toHaveBeenCalled();
  });

  it("hides Clear when not snoozed", async () => {
    renderTab();
    await screen.findByRole("button", { name: "1 hour" });
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });

  it("lists webhooks, toggles and deletes", async () => {
    api.updateWebhook.mockResolvedValue(HOOK);
    api.deleteWebhook.mockResolvedValue({ message: "ok" });
    const user = userEvent.setup();
    renderTab();
    expect(
      await screen.findByText("https://example.com/hook"),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("switch", { name: "Enabled https://example.com/hook" }),
    );
    expect(api.updateWebhook).toHaveBeenCalledWith("w1", { enabled: false });
    await user.click(
      screen.getByRole("button", { name: "Delete https://example.com/hook" }),
    );
    expect(api.deleteWebhook).toHaveBeenCalledWith("w1");
  });

  it("creates a webhook and shows the secret once", async () => {
    api.createWebhook.mockResolvedValue({
      id: "w2",
      url: "https://x.io/h",
      secret: "s3cret-value",
      type_keys: ["mention"],
      enabled: true,
    });
    const user = userEvent.setup();
    renderTab();
    await user.click(
      await screen.findByRole("button", { name: "Add webhook" }),
    );
    await user.type(screen.getByLabelText("URL"), "https://x.io/h");
    await user.click(await screen.findByRole("checkbox", { name: "mention" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.createWebhook).toHaveBeenCalledWith({
        url: "https://x.io/h",
        type_keys: ["mention"],
      }),
    );
    expect(await screen.findByText("s3cret-value")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy secret" }),
    ).toBeInTheDocument();
  });

  it("creates a disabled webhook when Enabled is switched off", async () => {
    api.createWebhook.mockResolvedValue({
      id: "w2",
      url: "https://x.io/h",
      secret: "s3cret-value",
      type_keys: ["mention"],
      enabled: true,
    });
    api.updateWebhook.mockResolvedValue({ ...HOOK, id: "w2", enabled: false });
    const user = userEvent.setup();
    renderTab();
    await user.click(
      await screen.findByRole("button", { name: "Add webhook" }),
    );
    await user.type(screen.getByLabelText("URL"), "https://x.io/h");
    await user.click(await screen.findByRole("checkbox", { name: "mention" }));
    await user.click(screen.getByRole("switch", { name: "Enabled" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.updateWebhook).toHaveBeenCalledWith("w2", { enabled: false }),
    );
  });

  it("edits a webhook without showing a secret", async () => {
    api.updateWebhook.mockResolvedValue(HOOK);
    const user = userEvent.setup();
    renderTab();
    await user.click(
      await screen.findByRole("button", {
        name: "Edit https://example.com/hook",
      }),
    );
    const url = screen.getByLabelText("URL");
    await user.clear(url);
    await user.type(url, "https://new.io/h");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.updateWebhook).toHaveBeenCalledWith("w1", {
        url: "https://new.io/h",
        type_keys: ["mention"],
        enabled: true,
      }),
    );
    expect(screen.queryByRole("button", { name: "Copy secret" })).toBeNull();
  });
});
