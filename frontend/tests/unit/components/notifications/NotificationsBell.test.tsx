/**
 * @file tests/unit/components/notifications/NotificationsBell.test.tsx
 * @brief NotificationsBell: red dot, active-only list as inbox rows, row
 *        opens the Inbox (marks read), mark all, SSE.
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
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}));
const nav = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => nav }));
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
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
vi.mock("@/components/inbox/useInboxItems", () => ({
  notifEntry: (n: { id: string; read_at?: string | null }) => ({
    kind: "notif",
    id: n.id,
    title: `row ${n.id}`,
    snippet: "",
    time: "2026-11-20T10:00:00Z",
    unread: !n.read_at,
  }),
}));

import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { useSession } from "@/stores/session";

const item = (id: string, read_at: string | null = null) => ({
  id,
  type: "mention",
  payload: {},
  read_at,
});
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
    api.markRead.mockResolvedValue({ message: "ok" });
    api.markAllRead.mockResolvedValue({ message: "ok" });
  });

  it("shows unread count in label and badge", async () => {
    setup();
    expect(
      await screen.findByRole("button", { name: "Notifications, 3 unread" }),
    ).toBeInTheDocument();
    // Brand: a quiet red dot, no number.
    expect(await screen.findByTestId("unread-badge")).toHaveTextContent("");
  });

  it("fetches active list only when open, never listNotifications", async () => {
    setup();
    await screen.findByTestId("unread-badge");
    expect(api.listActive).not.toHaveBeenCalled();
    await openBell();
    expect(await screen.findByText("row a")).toBeInTheDocument();
    expect(api.listNotifications).not.toHaveBeenCalled();
  });

  it("clicking an unread row marks it read and opens it in the Inbox", async () => {
    setup();
    await openBell();
    await userEvent.click(await screen.findByText("row a"));
    expect(api.markRead).toHaveBeenCalledWith("a");
    expect(nav.push).toHaveBeenCalledWith("/app/inbox?item=a");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clicking a read row does not call markRead", async () => {
    api.listActive.mockResolvedValue({ items: [item("r", "2026-11-20")] });
    setup();
    await openBell();
    await userEvent.click(await screen.findByText("row r"));
    expect(api.markRead).not.toHaveBeenCalled();
  });

  it("Mark all read calls the API; footer links to the Inbox", async () => {
    setup();
    await openBell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Mark all read" }),
    );
    expect(api.markAllRead).toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Open inbox" })).toHaveAttribute(
      "href",
      "/app/inbox",
    );
  });

  it("shows empty state", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 0 });
    api.listActive.mockResolvedValue({ items: [] });
    setup();
    await openBell();
    expect(
      await screen.findByText("You're all caught up."),
    ).toBeInTheDocument();
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

  it("SSE events invalidate the ['notifications'] caches", async () => {
    setup();
    await screen.findByTestId("unread-badge");
    const spy = vi.spyOn(qc, "invalidateQueries");
    expect(sse.opts?.eventTypes).toContain("user_preferences_updated");
    const on = sse.opts?.onMessage as (d: unknown, t: string) => void;
    on({}, "user_notification_dismissed");
    expect(spy).toHaveBeenCalledWith({ queryKey: ["notifications"] });
    on({}, "user_preferences_updated");
    expect(spy).toHaveBeenCalledWith({
      queryKey: ["notifications", "preferences"],
    });
  });
});
