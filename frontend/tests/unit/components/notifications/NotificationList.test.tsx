/**
 * @file tests/unit/components/notifications/NotificationList.test.tsx
 * @brief NotificationList: fetch, filter, selection passthrough, empty.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationList } from "@/components/notifications/NotificationList";
import { listNotifications } from "@/lib/api/notifications";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => `T:${k}`,
}));
vi.mock("@/lib/api/notifications", () => ({
  listNotifications: vi.fn(),
  dismissOne: vi.fn(),
  callAction: vi.fn(),
}));
vi.mock("@/components/notifications/NotifRow", () => ({
  NotifRow: (p: {
    item: { id: string };
    selected?: boolean;
    onSelectChange?: (id: string, s: boolean) => void;
  }) => (
    <div data-testid="row">
      {p.item.id}
      {p.onSelectChange && (
        <input
          type="checkbox"
          aria-label={`sel-${p.item.id}`}
          checked={!!p.selected}
          onChange={(e) => p.onSelectChange?.(p.item.id, e.target.checked)}
        />
      )}
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

function setup(items: unknown[], props = {}) {
  vi.mocked(listNotifications).mockResolvedValue({
    items,
    next_cursor: null,
    has_more: false,
  } as never);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <NotificationList filter="all" {...props} />
    </QueryClientProvider>,
  );
}

describe("NotificationList", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders all rows for filter=all", async () => {
    setup([mk("a"), mk("b", { read_at: "2026-01-02T00:00:00Z" })]);
    expect(await screen.findAllByTestId("row")).toHaveLength(2);
  });

  it("filter=unread hides read and dismissed", async () => {
    setup(
      [
        mk("a"),
        mk("b", { read_at: "2026-01-02T00:00:00Z" }),
        mk("c", { dismissed_at: "2026-01-02T00:00:00Z" }),
      ],
      { filter: "unread" },
    );
    expect(await screen.findAllByTestId("row")).toHaveLength(1);
  });

  it("passes selection to rows", async () => {
    const onSelectChange = vi.fn();
    setup([mk("a")], { selected: new Set(["a"]), onSelectChange });
    const box = await screen.findByLabelText("sel-a");
    expect(box).toBeChecked();
    await userEvent.click(box);
    expect(onSelectChange).toHaveBeenCalledWith("a", false);
  });

  it("does not fetch when disabled", () => {
    setup([mk("a")], { enabled: false });
    expect(listNotifications).not.toHaveBeenCalled();
  });

  it("shows empty state", async () => {
    setup([]);
    expect(
      await screen.findByText("T:notifications.drawer.empty"),
    ).toBeInTheDocument();
  });
});
