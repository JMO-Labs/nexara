/**
 * @file tests/unit/inbox/InboxPage.test.tsx
 * @brief /app/inbox: heading, ?view= tabs (notifications | saved | lists).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const nav = vi.hoisted(() => ({ qs: "", push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push }),
  useSearchParams: () => new URLSearchParams(nav.qs),
}));
vi.mock("@/components/inbox/NotificationsView", () => ({
  NotificationsView: () => <p>notifications view</p>,
}));
vi.mock("@/components/inbox/SavedView", () => ({
  SavedView: () => <p>saved view</p>,
}));
vi.mock("@/components/lists/pages/ListsBrowseView", () => ({
  ListsBrowseView: (p: { embedded?: boolean }) => (
    <p>lists view {p.embedded ? "embedded" : "full"}</p>
  ),
}));

import { InboxPage } from "@/components/inbox/InboxPage";

beforeEach(() => {
  nav.qs = "";
  nav.push.mockClear();
});

describe("InboxPage", () => {
  it("renders the Inbox heading and description", () => {
    render(<InboxPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Inbox" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Notifications, saved posts and your lists."),
    ).toBeInTheDocument();
  });

  it("shows notifications by default", () => {
    render(<InboxPage />);
    expect(screen.getByText("notifications view")).toBeInTheDocument();
    expect(screen.queryByText("saved view")).toBeNull();
  });

  it("shows saved when ?view=saved", () => {
    nav.qs = "view=saved";
    render(<InboxPage />);
    expect(screen.getByText("saved view")).toBeInTheDocument();
    expect(screen.queryByText("notifications view")).toBeNull();
  });

  it("shows the embedded lists view when ?view=lists", () => {
    nav.qs = "view=lists";
    render(<InboxPage />);
    expect(screen.getByText("lists view embedded")).toBeInTheDocument();
  });

  it("pushes ?view=saved when Saved is chosen", async () => {
    render(<InboxPage />);
    await userEvent.click(screen.getByRole("radio", { name: "Saved" }));
    expect(nav.push).toHaveBeenCalledWith("/app/inbox?view=saved");
  });

  it("pushes the bare /app/inbox when Notifications is chosen", async () => {
    nav.qs = "view=lists";
    render(<InboxPage />);
    await userEvent.click(screen.getByRole("radio", { name: "Notifications" }));
    expect(nav.push).toHaveBeenCalledWith("/app/inbox");
  });
});
