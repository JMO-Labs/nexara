/**
 * @file tests/unit/notifications/NotificationsStates.test.tsx
 * @brief Empty/error states, unread dot, keyboard access for rows.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  getUnreadCount: vi.fn(),
  listNotifications: vi.fn(),
  markAllRead: vi.fn(),
  markRead: vi.fn(),
}));
vi.mock("@/lib/api/notifications", () => ({ ...api, STREAM_PATH: "/s" }));
vi.mock("@/hooks/useSSE", () => ({ useSSE: vi.fn() }));

import { NotificationsBell } from "@/components/notifications/NotificationsBell";
import { useSession } from "@/stores/session";

const item = (id: string, read_at: string | null, link?: string) => ({
  id,
  type: "mention",
  created_at: new Date().toISOString(),
  read_at,
  payload: { message: `msg ${id}`, ...(link ? { link } : {}) },
});

async function openPanel(name: string) {
  useSession.setState({ status: "authenticated" } as never);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <NotificationsBell />
    </QueryClientProvider>,
  );
  await userEvent.click(await screen.findByRole("button", { name }));
}

async function tabTo(el: HTMLElement) {
  for (let i = 0; i < 10 && document.activeElement !== el; i++) {
    await userEvent.tab();
  }
}

describe("Notifications states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getUnreadCount.mockResolvedValue({ count: 0 });
    api.markRead.mockResolvedValue(undefined);
  });

  it("empty state has icon, title and description", async () => {
    api.listNotifications.mockResolvedValue({ items: [] });
    await openPanel("Notifications");
    expect(await screen.findByText("No notifications")).toBeInTheDocument();
    expect(screen.getByTestId("notifications-empty-icon")).toBeInTheDocument();
    expect(
      screen.getByText(/you're all caught up|new activity/i),
    ).toBeInTheDocument();
  });

  it("error state offers Retry that refetches", async () => {
    api.listNotifications.mockRejectedValueOnce(new Error("boom"));
    api.listNotifications.mockResolvedValue({ items: [] });
    await openPanel("Notifications");
    expect(
      await screen.findByText("Failed to load notifications"),
    ).toBeInTheDocument();
    const calls = api.listNotifications.mock.calls.length;
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(api.listNotifications.mock.calls.length).toBeGreaterThan(calls);
    expect(await screen.findByText("No notifications")).toBeInTheDocument();
  });

  it("unread rows show labelled dot; read rows do not", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 1 });
    api.listNotifications.mockResolvedValue({
      items: [item("a", null), item("b", "x")],
    });
    await openPanel("Notifications, 1 unread");
    await screen.findByText("msg a");
    expect(screen.getAllByLabelText("Unread")).toHaveLength(1);
  });

  it("link rows are tabbable and open on Enter", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 1 });
    api.listNotifications.mockResolvedValue({
      items: [item("a", null, "/posts/1")],
    });
    await openPanel("Notifications, 1 unread");
    const row = (await screen.findByText("msg a")).closest("a")!;
    expect(row).toHaveAttribute("href", "/posts/1");
    await tabTo(row);
    expect(document.activeElement).toBe(row);
    await userEvent.keyboard("{Enter}");
    expect(api.markRead).toHaveBeenCalledWith("a");
  });

  it("non-link unread rows are focusable and ack on Enter", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 1 });
    api.listNotifications.mockResolvedValue({ items: [item("a", null)] });
    await openPanel("Notifications, 1 unread");
    const row = (await screen.findByText("msg a")).closest(
      "[data-row]",
    ) as HTMLElement;
    expect(row).toHaveAttribute("tabindex", "0");
    await tabTo(row);
    expect(document.activeElement).toBe(row);
    await userEvent.keyboard("{Enter}");
    expect(api.markRead).toHaveBeenCalledWith("a");
  });
});
