/**
 * @file tests/unit/components/notifications/NotifRow.test.tsx
 * @brief Registry-driven NotifRow: render, actions, link, ack, select.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NotifRow } from "@/components/notifications/NotifRow";
import type {
  NotificationItem,
  NotificationTypeDescriptor,
} from "@/lib/notifications/types";
import { callAction, dismissOne } from "@/lib/api/notifications";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => `T:${k}`,
}));
vi.mock("@/lib/api/notifications", () => ({
  callAction: vi.fn(),
  dismissOne: vi.fn(),
}));

const type: NotificationTypeDescriptor = {
  key: "event.invite",
  category: "event",
  default_channels: {
    inapp: true,
    email: false,
    push: false,
    webhook: false,
    toast: false,
  },
  user_configurable: [],
  group_window_seconds: null,
  toast_on_arrival: false,
  bypass_dnd: false,
  digestable: false,
  actions: [
    {
      key: "accept",
      label_i18n: "act.accept",
      method: "POST",
      url_template: "/x/{id}",
      style: "primary",
    },
  ],
  label_i18n: "type.invite",
  icon: "calendar",
  plugin_id: null,
  payload_schema: {},
};

const item = (o: Partial<NotificationItem> = {}): NotificationItem => ({
  id: "n1",
  user_id: "u1",
  type: "event.invite",
  payload: { message: "Hello body" },
  read_at: null,
  dismissed_at: null,
  created_at: "2026-01-01T10:00:00Z",
  updated_at: "2026-01-01T10:00:00Z",
  count: 1,
  actor_ids: [],
  ...o,
});

describe("NotifRow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(callAction).mockResolvedValue({ message: "ok" });
    vi.mocked(dismissOne).mockResolvedValue({ message: "ok" });
  });

  it("renders title, body and action buttons", () => {
    render(<NotifRow item={item()} type={type} onDismissed={vi.fn()} />);
    expect(screen.getByText("T:type.invite")).toBeInTheDocument();
    expect(screen.getByText("Hello body")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "T:act.accept" }),
    ).toBeInTheDocument();
  });

  it("action click calls callAction then onDismissed", async () => {
    const onDismissed = vi.fn();
    render(<NotifRow item={item()} type={type} onDismissed={onDismissed} />);
    await userEvent.click(screen.getByRole("button", { name: "T:act.accept" }));
    await waitFor(() => expect(onDismissed).toHaveBeenCalledWith("n1"));
    expect(callAction).toHaveBeenCalledWith("n1", "accept");
  });

  it("does not dismiss when the action fails", async () => {
    vi.mocked(callAction).mockRejectedValue(new Error("boom"));
    const onDismissed = vi.fn();
    render(<NotifRow item={item()} type={type} onDismissed={onDismissed} />);
    await userEvent.click(screen.getByRole("button", { name: "T:act.accept" }));
    await waitFor(() => expect(callAction).toHaveBeenCalled());
    expect(onDismissed).not.toHaveBeenCalled();
  });

  it("ack button dismisses unread item", async () => {
    const onDismissed = vi.fn();
    render(<NotifRow item={item()} type={type} onDismissed={onDismissed} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Acknowledge notification" }),
    );
    await waitFor(() => expect(onDismissed).toHaveBeenCalledWith("n1"));
    expect(dismissOne).toHaveBeenCalledWith("n1");
  });

  it("hides ack and unread styling when read", () => {
    render(
      <NotifRow
        item={item({ read_at: "2026-01-01T11:00:00Z" })}
        type={type}
        onDismissed={vi.fn()}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Acknowledge notification" }),
    ).toBeNull();
    expect(screen.getByTestId("notif-row")).toHaveAttribute(
      "data-unread",
      "false",
    );
  });

  it("marks unread rows", () => {
    render(<NotifRow item={item()} type={type} onDismissed={vi.fn()} />);
    expect(screen.getByTestId("notif-row")).toHaveAttribute(
      "data-unread",
      "true",
    );
  });

  it("wraps in a link that dismisses on click", async () => {
    render(
      <NotifRow
        item={item({ payload: { message: "m", link: "/app/events/1" } })}
        type={{ ...type, actions: [] }}
        onDismissed={vi.fn()}
      />,
    );
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/app/events/1");
    await userEvent.click(link);
    expect(dismissOne).toHaveBeenCalledWith("n1");
  });

  it("renders no link for external/unsafe urls", () => {
    render(
      <NotifRow
        item={item({ payload: { message: "m", link: "https://evil.example" } })}
        type={type}
        onDismissed={vi.fn()}
      />,
    );
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("checkbox reports selection", async () => {
    const onSelectChange = vi.fn();
    render(
      <NotifRow
        item={item()}
        type={type}
        onDismissed={vi.fn()}
        selected={false}
        onSelectChange={onSelectChange}
      />,
    );
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onSelectChange).toHaveBeenCalledWith("n1", true);
  });

  it("no checkbox without onSelectChange", () => {
    render(<NotifRow item={item()} type={type} onDismissed={vi.fn()} />);
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});
