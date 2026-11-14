/**
 * @file tests/unit/components/notifications/NotificationsDrawer.test.tsx
 * @brief Drawer: open on event, filters, selection, bulk dismiss, empty.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationsDrawer } from "@/components/notifications/NotificationsDrawer";
import { dismissOne, listNotifications } from "@/lib/api/notifications";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => `T:${k}`,
}));
vi.mock("@/lib/api/notifications", () => ({
  listNotifications: vi.fn(),
  dismissOne: vi.fn(),
  callAction: vi.fn(),
  STREAM_PATH: "/s",
}));
import { useSSE } from "@/hooks/useSSE";
vi.mock("@/hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("@/components/notifications/NotifRow", () => ({
  NotifRow: (p: {
    item: { id: string };
    selected?: boolean;
    onSelectChange?: (id: string, s: boolean) => void;
  }) => (
    <div data-testid="row">
      {p.item.id}
      <input
        type="checkbox"
        aria-label={`sel-${p.item.id}`}
        checked={!!p.selected}
        onChange={(e) => p.onSelectChange?.(p.item.id, e.target.checked)}
      />
    </div>
  ),
}));
vi.mock("@/lib/notifications/registry", () => ({
  useNotificationRegistry: () => ({
    byKey: new Map([["event.invite", { key: "event.invite", actions: [] }]]),
  }),
}));

const mk = (id: string, extra = {}) => ({
  id,
  user_id: "u",
  type: "event.invite",
  payload: {},
  read_at: null,
  dismissed_at: null,
  created_at: "2026-01-01T00:00:00Z",
  ...extra,
});

function setup(items: unknown[]) {
  vi.mocked(listNotifications).mockResolvedValue({
    items,
    next_cursor: null,
    has_more: false,
  } as never);
  vi.mocked(dismissOne).mockResolvedValue({ message: "ok" });
  const qc = new QueryClient();
  render(
    <QueryClientProvider client={qc}>
      <NotificationsDrawer />
    </QueryClientProvider>,
  );
  return qc;
}
const open = () =>
  act(() => {
    window.dispatchEvent(new CustomEvent("notifications:drawer-open"));
  });

describe("NotificationsDrawer", () => {
  beforeEach(() => vi.clearAllMocks());

  it("is closed until the open event fires", async () => {
    setup([mk("a")]);
    expect(screen.queryByText("T:notifications.drawer.title")).toBeNull();
    open();
    expect(
      await screen.findByText("T:notifications.drawer.title"),
    ).toBeInTheDocument();
    expect(await screen.findAllByTestId("row")).toHaveLength(1);
  });

  it("subscribes to sync events and invalidates matching keys", () => {
    const qc = setup([]);
    const opts = vi.mocked(useSSE).mock.calls.at(-1)![1] as {
      eventTypes: string[];
      onMessage: (d: unknown, t: string) => void;
    };
    expect(opts.eventTypes).toEqual(
      expect.arrayContaining([
        "user_notification_dismissed",
        "user_preferences_updated",
      ]),
    );
    const spy = vi.spyOn(qc, "invalidateQueries");
    opts.onMessage({}, "user_notification_dismissed");
    expect(spy).toHaveBeenCalledWith({ queryKey: ["notifications"] });
    opts.onMessage({}, "user_preferences_updated");
    expect(spy).toHaveBeenCalledWith({
      queryKey: ["notifications", "preferences"],
    });
  });

  it("Unread filter hides read and dismissed", async () => {
    setup([
      mk("a"),
      mk("b", { read_at: "2026-01-02T00:00:00Z" }),
      mk("c", { dismissed_at: "2026-01-02T00:00:00Z" }),
    ]);
    open();
    expect(await screen.findAllByTestId("row")).toHaveLength(3);
    await userEvent.click(
      screen.getByRole("button", { name: "T:notifications.filter.unread" }),
    );
    expect(screen.getAllByTestId("row")).toHaveLength(1);
    await userEvent.click(
      screen.getByRole("button", { name: "T:notifications.filter.all" }),
    );
    expect(screen.getAllByTestId("row")).toHaveLength(3);
  });

  it("selection shows bulk toolbar; dismiss selected calls dismissOne", async () => {
    const qc = setup([mk("a"), mk("b")]);
    const spy = vi.spyOn(qc, "invalidateQueries");
    open();
    await screen.findAllByTestId("row");
    expect(
      screen.queryByRole("button", { name: "T:notifications.bulk.dismiss" }),
    ).toBeNull();
    await userEvent.click(screen.getByLabelText("sel-a"));
    await userEvent.click(screen.getByLabelText("sel-b"));
    await userEvent.click(
      screen.getByRole("button", { name: "T:notifications.bulk.dismiss" }),
    );
    await waitFor(() => expect(dismissOne).toHaveBeenCalledTimes(2));
    expect(dismissOne).toHaveBeenCalledWith("a");
    expect(dismissOne).toHaveBeenCalledWith("b");
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(
      screen.queryByRole("button", { name: "T:notifications.bulk.dismiss" }),
    ).toBeNull();
  });

  it("shows empty state", async () => {
    setup([]);
    open();
    expect(
      await screen.findByText("T:notifications.drawer.empty"),
    ).toBeInTheDocument();
  });
});
