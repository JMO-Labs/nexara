/**
 * @file tests/unit/notifications/NotificationsBell.test.tsx
 * @brief NotificationsBell: unread label, panel list, ack, mark all read.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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

function setup() {
  useSession.setState({ status: "authenticated" } as never);
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <NotificationsBell />
    </QueryClientProvider>,
  );
}

describe("NotificationsBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getUnreadCount.mockResolvedValue({ count: 3 });
    api.listNotifications.mockResolvedValue({
      items: [item("a", null), item("b", "x")],
    });
    api.markAllRead.mockResolvedValue(undefined);
    api.markRead.mockResolvedValue(undefined);
  });

  it("announces unread count in the label", async () => {
    setup();
    expect(
      await screen.findByRole("button", { name: "Notifications, 3 unread" }),
    ).toBeInTheDocument();
  });

  it("uses plain label when nothing unread", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 0 });
    setup();
    expect(
      await screen.findByRole("button", { name: "Notifications" }),
    ).toBeInTheDocument();
  });

  it("opens the panel and lists items; Escape closes", async () => {
    setup();
    await userEvent.click(
      await screen.findByRole("button", { name: /Notifications/ }),
    );
    expect(await screen.findByText("msg a")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Notifications" })).toBeVisible();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("acknowledges one unread row", async () => {
    setup();
    await userEvent.click(
      await screen.findByRole("button", { name: /Notifications/ }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Acknowledge notification" }),
    );
    await waitFor(() => expect(api.markRead).toHaveBeenCalledWith("a"));
  });

  it("marks all read", async () => {
    setup();
    await userEvent.click(
      await screen.findByRole("button", { name: /Notifications/ }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Mark all read" }),
    );
    await waitFor(() => expect(api.markAllRead).toHaveBeenCalled());
  });

  it("shows empty state", async () => {
    api.getUnreadCount.mockResolvedValue({ count: 0 });
    api.listNotifications.mockResolvedValue({ items: [] });
    setup();
    await userEvent.click(
      await screen.findByRole("button", { name: "Notifications" }),
    );
    expect(await screen.findByText("No notifications")).toBeInTheDocument();
  });
});
