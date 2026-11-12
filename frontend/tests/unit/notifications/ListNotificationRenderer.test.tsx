/**
 * @file tests/unit/notifications/ListNotificationRenderer.test.tsx
 * @brief List notification renderers: title, details, dismiss, navigate.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  ListNotification,
  isListNotificationType,
  LIST_TITLES,
} from "@/components/notifications/ListNotificationRenderer";

const ctx = {
  listId: "L1",
  listName: "My Gift List",
  userName: "Ann",
  inviterName: "Bob",
  itemTitle: "Socks",
};
const mk = (type: string) => ({
  id: "n1",
  type,
  context: ctx,
  createdAt: new Date(Date.now() - 5 * 60_000).toISOString(),
});

describe("ListNotification", () => {
  it.each([
    ["list.item", "New item in My Gift List"],
    ["list.signup", "Ann claimed"],
    ["list.completed", "Item marked done"],
    ["list.expiring", "Expires in 1 day"],
    ["list.member", "Added by Bob"],
  ])("renders %s title", (type, title) => {
    render(
      <ListNotification
        notification={mk(type)}
        onDismiss={vi.fn()}
        onNavigate={vi.fn()}
        href="/app/lists/L1"
      />,
    );
    expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByText("5m ago")).toBeInTheDocument();
    expect(screen.getByText("Socks")).toBeInTheDocument();
  });

  it("navigates with listId on row click", async () => {
    const onNavigate = vi.fn();
    render(
      <ListNotification
        notification={mk("list.item")}
        onDismiss={vi.fn()}
        onNavigate={onNavigate}
        href="/app/lists/L1"
      />,
    );
    await userEvent.click(screen.getByText("New item in My Gift List"));
    expect(onNavigate).toHaveBeenCalledWith("L1");
  });

  it("dismiss calls onDismiss(id) without navigating", async () => {
    const onDismiss = vi.fn();
    const onNavigate = vi.fn();
    render(
      <ListNotification
        notification={mk("list.item")}
        onDismiss={onDismiss}
        onNavigate={onNavigate}
        href="/app/lists/L1"
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledWith("n1");
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("detects list types", () => {
    expect(isListNotificationType("list.item")).toBe(true);
    expect(isListNotificationType("mention")).toBe(false);
    expect(Object.keys(LIST_TITLES)).toHaveLength(5);
  });
});
