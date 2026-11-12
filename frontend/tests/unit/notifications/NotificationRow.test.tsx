/**
 * @file tests/unit/notifications/NotificationRow.test.tsx
 * @brief NotificationRow: text, unread state, ack/dismiss/navigate handlers.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { NotificationRow } from "@/components/notifications/NotificationRow";
import type { NotificationItem } from "@/lib/api/notifications";

const item = (over: Partial<NotificationItem> = {}): NotificationItem => ({
  id: "n1",
  user_id: "u1",
  type: "comment",
  payload: { message: "Bob commented" },
  read_at: null,
  created_at: new Date().toISOString(),
  ...over,
});

function setup(i: NotificationItem, ackPending = false) {
  const h = { onAck: vi.fn(), onDismiss: vi.fn(), onNavigate: vi.fn() };
  renderWithProviders(
    <NotificationRow item={i} ackPending={ackPending} {...h} />,
  );
  return h;
}

describe("NotificationRow", () => {
  it("renders message, type label and relative time", () => {
    setup(item());
    expect(screen.getByText("Bob commented")).toBeInTheDocument();
    expect(screen.getByLabelText("Comment")).toBeInTheDocument();
    expect(screen.getByText("just now")).toBeInTheDocument();
  });

  it("falls back to the type label when no message", () => {
    setup(item({ type: "event_rsvp", payload: {} }));
    expect(screen.getByText("Event RSVP")).toBeInTheDocument();
  });

  it("humanizes unknown types", () => {
    setup(item({ type: "some_new_type", payload: {} }));
    expect(screen.getByText("some new type")).toBeInTheDocument();
  });

  it("unread shows ack button that calls onAck", async () => {
    const h = setup(item());
    await userEvent.click(
      screen.getByRole("button", { name: "Acknowledge notification" }),
    );
    expect(h.onAck).toHaveBeenCalledWith("n1");
  });

  it("disables ack while pending", () => {
    setup(item(), true);
    expect(
      screen.getByRole("button", { name: "Acknowledge notification" }),
    ).toBeDisabled();
  });

  it("read item has no ack button", () => {
    setup(item({ read_at: new Date().toISOString() }));
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("safe link navigates and dismisses; ack does not navigate", async () => {
    const h = setup(item({ payload: { message: "m", link: "/events/1" } }));
    expect(screen.getByRole("link")).toHaveAttribute("href", "/events/1");
    await userEvent.click(
      screen.getByRole("button", { name: "Acknowledge notification" }),
    );
    expect(h.onDismiss).not.toHaveBeenCalled();
    await userEvent.click(screen.getByText("m"));
    expect(h.onDismiss).toHaveBeenCalledWith("n1");
    expect(h.onNavigate).toHaveBeenCalled();
  });

  it("unsafe link renders no anchor", () => {
    setup(item({ payload: { message: "m", link: "//evil.com" } }));
    expect(screen.queryByRole("link")).toBeNull();
  });
});

describe("NotificationRow list types", () => {
  it("renders list renderer and navigates to /app/lists/[id]", async () => {
    const onNavigate = vi.fn();
    const onDismiss = vi.fn();
    renderWithProviders(
      <NotificationRow
        item={{
          ...item(),
          id: "n9",
          type: "list.item",
          payload: { listId: "L9", listName: "Trip" },
        }}
        onAck={vi.fn()}
        onDismiss={onDismiss}
        onNavigate={onNavigate}
        ackPending={false}
      />,
    );
    expect(screen.getByText("New item in Trip")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledWith("n9");
    expect(onNavigate).not.toHaveBeenCalled();
  });

  const listItem = (over: Partial<NotificationItem> = {}) =>
    item({
      id: "n9",
      type: "list.item",
      payload: { listId: "L9", listName: "Trip" },
      ...over,
    });

  it("is a real link to /app/lists/[id]; click dismisses and navigates", async () => {
    const h = setup(listItem());
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/app/lists/L9");
    await userEvent.click(link);
    expect(h.onDismiss).toHaveBeenCalledWith("n9");
    expect(h.onNavigate).toHaveBeenCalled();
  });

  it("encodes the list id in the href", () => {
    setup(listItem({ payload: { listId: "a/b" } }));
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/app/lists/a%2Fb",
    );
  });

  it("unread list notification can be acknowledged without navigating", async () => {
    const h = setup(listItem());
    await userEvent.click(
      screen.getByRole("button", { name: "Acknowledge notification" }),
    );
    expect(h.onAck).toHaveBeenCalledWith("n9");
    expect(h.onNavigate).not.toHaveBeenCalled();
  });

  it("read list notification has no ack button", () => {
    setup(listItem({ read_at: new Date().toISOString() }));
    expect(
      screen.queryByRole("button", { name: "Acknowledge notification" }),
    ).toBeNull();
  });
});
