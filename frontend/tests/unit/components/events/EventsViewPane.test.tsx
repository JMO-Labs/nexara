/**
 * @file tests/unit/components/events/EventsViewPane.test.tsx
 * @brief EventsViewPane: loading/empty/error states and month-sticky list.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  EventsViewPane,
  type EventsViewPaneProps,
} from "@/components/events/events-page/EventsViewPane";

vi.mock("@/components/events/MonthCalendarLarge", () => ({
  MonthCalendarLarge: () => <div>month-grid</div>,
}));

const ev = (id: string, title: string, starts_at: string): any => ({
  id,
  title,
  starts_at,
  ends_at: starts_at,
});

function setup(over: Partial<EventsViewPaneProps> = {}) {
  const props: EventsViewPaneProps = {
    view: "list",
    events: [],
    status: "ready",
    onRetry: vi.fn(),
    onCreate: vi.fn(),
    month: new Date(2025, 0, 1),
    weekStart: new Date(2025, 0, 5),
    onWeekStartChange: vi.fn(),
    selectedDay: null,
    onSelectedDayChange: vi.fn(),
    selectedEventId: null,
    subgroupNames: new Map(),
    onSelectDay: vi.fn(),
    onSelectEvent: vi.fn(),
    ...over,
  };
  render(<EventsViewPane {...props} />);
  return props;
}

describe("EventsViewPane states", () => {
  it("loading shows one busy status with staggered skeletons", () => {
    setup({ status: "loading" });
    const st = screen.getAllByRole("status");
    expect(st).toHaveLength(1);
    expect(st[0].getAttribute("aria-busy")).toBe("true");
    expect(screen.queryByText("month-grid")).toBeNull();
  });

  it("error shows Retry that calls onRetry", async () => {
    const p = setup({ status: "error" });
    expect(screen.getByText(/couldn't load events/i)).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(p.onRetry).toHaveBeenCalled();
  });

  it("empty shows 'No events. Create one!' CTA calling onCreate", async () => {
    const p = setup({ events: [] });
    expect(screen.getByText(/no events\. create one!/i)).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: /create event/i }),
    );
    expect(p.onCreate).toHaveBeenCalled();
  });

  it("empty month view keeps the grid visible", () => {
    setup({ view: "month", events: [] });
    expect(screen.getByText("month-grid")).toBeTruthy();
    expect(screen.getByText(/no events\. create one!/i)).toBeTruthy();
  });

  it("list view groups by month under sticky headings", () => {
    setup({
      events: [
        ev("1", "A", "2025-01-10T12:00:00"),
        ev("2", "B", "2025-02-05T12:00:00"),
      ],
    });
    const heads = screen.getAllByRole("heading", { level: 2 });
    expect(heads.map((h) => h.textContent)).toEqual([
      "January 2025",
      "February 2025",
    ]);
    expect(heads[0].className).toMatch(/(^|\s)sticky(\s|$)/);
  });
});
