/**
 * @file tests/unit/inbox/InboxPage.test.tsx
 * @brief Outlook-style Inbox: folder rail, row selection (?item=), mark read
 *        on open, reading pane and empty states.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const nav = vi.hoisted(() => ({ qs: "", push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push }),
  useSearchParams: () => new URLSearchParams(nav.qs),
}));
const api = vi.hoisted(() => ({
  markRead: vi.fn(() => Promise.resolve({ message: "ok" })),
  markAllRead: vi.fn(() => Promise.resolve({ message: "ok" })),
}));
vi.mock("@/lib/api/notifications", () => api);
vi.mock("@/hooks/useNotificationsSync", () => ({
  useNotificationsSync: () => {},
}));
const data = vi.hoisted(() => ({ items: [] as unknown[], unread: 0 }));
vi.mock("@/components/inbox/useInboxItems", () => ({
  useInboxItems: (folder: string) => ({
    items: data.items,
    isLoading: false,
    unreadCount: data.unread,
    saved: { hasNextPage: false },
    folder,
  }),
}));
vi.mock("@/components/inbox/ReadingPane", () => ({
  ReadingPane: (p: { entry: { title: string } | null }) => (
    <p>pane: {p.entry ? p.entry.title : "empty"}</p>
  ),
}));

import { InboxPage } from "@/components/inbox/InboxPage";

const notif = (id: string, unread: boolean) => ({
  kind: "notif",
  id,
  title: `Title ${id}`,
  snippet: "body",
  time: "2026-11-20T10:00:00Z",
  unread,
});
const ui = () => (
  <QueryClientProvider client={new QueryClient()}>
    <InboxPage />
  </QueryClientProvider>
);

beforeEach(() => {
  nav.qs = "";
  nav.push.mockClear();
  api.markRead.mockClear();
  data.items = [notif("n1", true), notif("n2", false)];
  data.unread = 1;
});

describe("InboxPage", () => {
  it("renders folder rail, rows and an empty reading pane", () => {
    render(ui());
    const rail = screen.getByRole("navigation", { name: "Inbox folders" });
    for (const f of ["Notifications", "Unread", "Saved", "Lists"])
      expect(
        within(rail).getByRole("button", { name: new RegExp(f) }),
      ).toBeInTheDocument();
    expect(screen.getAllByTestId("inbox-row")).toHaveLength(2);
    expect(screen.getByText("pane: empty")).toBeInTheDocument();
  });

  it("opening an unread row marks it read and pushes ?item=", async () => {
    render(ui());
    await userEvent.click(screen.getByText("Title n1"));
    expect(api.markRead).toHaveBeenCalledWith("n1");
    expect(nav.push).toHaveBeenCalledWith("/app/inbox?item=n1");
  });

  it("does not mark an already-read row", async () => {
    render(ui());
    await userEvent.click(screen.getByText("Title n2"));
    expect(api.markRead).not.toHaveBeenCalled();
  });

  it("shows the selected entry in the reading pane", () => {
    nav.qs = "item=n2";
    render(ui());
    expect(screen.getByText("pane: Title n2")).toBeInTheDocument();
  });

  it("switching folders drops the item and keeps view", async () => {
    nav.qs = "item=n2";
    render(ui());
    const rail = screen.getByRole("navigation", { name: "Inbox folders" });
    await userEvent.click(within(rail).getByRole("button", { name: /Saved/ }));
    expect(nav.push).toHaveBeenCalledWith("/app/inbox?view=saved");
  });

  it("shows a folder empty state", () => {
    nav.qs = "view=unread";
    data.items = [];
    render(ui());
    expect(screen.getByText("You're all caught up")).toBeInTheDocument();
  });
});
