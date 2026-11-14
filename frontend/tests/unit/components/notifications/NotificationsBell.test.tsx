/**
 * @file tests/unit/components/notifications/NotificationsBell.test.tsx
 * @brief NotificationsBell: active-only list, badge, dismiss, drawer, SSE.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  getUnreadCount: vi.fn(),
  listActive: vi.fn(),
  listNotifications: vi.fn(),
  dismissOne: vi.fn(),
}));
const sse = vi.hoisted(() => ({
  opts: null as null | Record<string, unknown>,
}));
vi.mock("@/lib/api/notifications", () => ({ ...api, STREAM_PATH: "/s" }));
vi.mock("@/hooks/useSSE", () => ({
  useSSE: (_p: string, o: Record<string, unknown>) => {
    sse.opts = o;
  },
}));
vi.mock("@/lib/notifications/registry", () => ({
  useNotificationRegistry: () => ({
    byKey: new Map([["mention", { key: "mention" }]]),
  }),
}));
vi.mock("@/components/notifications/NotifRow", () => ({
  NotifRow: ({
    item,
    onDismissed,
  }: {
    item: { id: string };
    onDismissed: (id: string) => void;
  }) => <button onClick={() => onDismissed(item.id)}>row {item.id}</button>,
}));

import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { useSession } from "@/stores/session";

const item = (id: string) => ({ id, type: "mention", payload: {} });
let qc: QueryClient;

function setup() {
  useSession.setState({ status: "authenticated" } as never);
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NotificationsBell />
    </QueryClientProvider>,
  );
}
const openBell = async () =>
  userEvent.click(await screen.findByRole("button", { name: /Notifications/ }));

describe("NotificationsBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getUnreadCount.mockResolvedValue({ count: 3 });
    api.listActive.mockResolvedValue({ items: [item("a"), item("b")] });
    api.dismissOne.mockResolvedValue({ message: "ok" });
  });

  it("shows unread count in label and badge", async () => {
    setup();
    expect(
      await screen.findByRole("button", { name: "Notifications, 3 unread" }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId("unread-badge")).toHaveTextContent("3");
  });

  it("fetches active list only when open, never listNotifications", async () => {
    setup();
    await screen.findByTestId("unread-badge");
    expect(api.listActive).not.toHaveBeenCalled();
    await openBell();
    expect(await screen.findByText("row a")).toBeInTheDocument();
    expect(api.listNotifications).not.toHaveBeenCalled();
  });

  it("dismissing a row removes it optimistically", async () => {
    setup();
    await openBell();
    await userEvent.click(await screen.findByText("row a"));
    await waitFor(() =>
      expect(screen.queryByText("row a")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("row b")).toBeInTheDocument();
  });

  it("View all dispatches drawer-open event", async () => {
    setup();
    const spy = vi.fn();
    window.addEventListener("notifications:drawer-open", spy);
    await openBell();
    await userEvent.click(
      await screen.findByRole("button", { name: "View all" }),
    );
    expect(spy).toHaveBeenCalled();
    window.removeEventListener("notifications:drawer-open", spy);
  });

  it("shows empty state", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 0 });
    api.listActive.mockResolvedValue({ items: [] });
    setup();
    await openBell();
    expect(await screen.findByText("All caught up.")).toBeInTheDocument();
  });

  it("Escape closes the panel", async () => {
    setup();
    await openBell();
    await screen.findByText("row a");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("SSE dismissed event invalidates active and count", async () => {
    setup();
    await screen.findByTestId("unread-badge");
    const spy = vi.spyOn(qc, "invalidateQueries");
    expect(sse.opts?.eventTypes).toContain("user_notification_dismissed");
    (sse.opts?.onMessage as () => void)();
    expect(spy).toHaveBeenCalledWith({ queryKey: ["notif", "active"] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["notif", "count"] });
  });
});
