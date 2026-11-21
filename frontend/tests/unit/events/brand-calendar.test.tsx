/**
 * @file tests/unit/events/brand-calendar.test.tsx
 * @brief Brand rules for calendar surfaces: no left colour rails, no hard
 *        grid lines, centred weekday labels, friendly hour and date labels.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { format, parseISO, startOfWeek } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { MonthCalendarLarge } from "@/components/events/MonthCalendarLarge";
import { WeekView } from "@/components/events/WeekView";
import { ListView } from "@/components/events/ListView";
import { EventRail } from "@/components/events/EventRail";
import { formatTime } from "@/components/events/formatTime";
import { chipStyle } from "@/components/events/toneStyle";

const base = {
  author_id: "u1",
  description: null,
  location: null,
  is_all_day: false,
  recurrence_rule: null,
  visibility: "community",
  subgroup_id: null,
  subgroup_slug: null,
  calendar_id: null,
  color: null,
  latitude: null,
  longitude: null,
  rsvp_labels: {},
  rsvp_counts: {},
  contribution_slots: [],
  user_rsvp: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
} as const;

const ev = (
  id: string,
  title: string,
  starts_at: string,
  ends_at: string,
): EventItem =>
  ({ ...base, id, title, starts_at, ends_at }) as unknown as EventItem;

// Sunday 2026-11-01 is the first cell of the November grid.
const NOV_1 = "2026-11-01T10:00:00";
const NOV_1_END = "2026-11-01T11:00:00";
const NOV_21 = "2026-11-21T09:00:00";
const NOV_21_END = "2026-11-21T11:00:00";

describe("formatTime", () => {
  it("lowercases and drops zero minutes", () => {
    expect(formatTime(new Date(2026, 10, 21, 9, 0))).toBe("9 am");
    expect(formatTime(new Date(2026, 10, 21, 9, 30))).toBe("9:30 am");
    expect(formatTime(new Date(2026, 10, 21, 0, 0))).toBe("12 am");
    expect(formatTime(new Date(2026, 10, 21, 13, 0))).toBe("1 pm");
  });
});

describe("chipStyle", () => {
  it("does not set a border colour (no left rail)", () => {
    const s = chipStyle({ solid: "#123456" } as never, false);
    expect(s.borderColor).toBeUndefined();
  });
});

describe("MonthCalendarLarge brand", () => {
  const month = new Date(2026, 10, 1);
  const events = [ev("m1", "Picnic", NOV_1, NOV_1_END)];

  it("event bars have no left border rail and carry a colour dot", () => {
    render(
      <MonthCalendarLarge
        events={events}
        month={month}
        selectedDay={null}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectDay={vi.fn()}
        onSelectEvent={vi.fn()}
      />,
    );
    const bar = screen.getByRole("button", { name: /Picnic/ });
    expect(bar.className).not.toContain("border-l");
    expect(
      bar.querySelector('[aria-hidden="true"].rounded-full'),
    ).not.toBeNull();
  });

  it("cells have no hairline borders and use rounded glass tiles", () => {
    render(
      <MonthCalendarLarge
        events={[]}
        month={month}
        selectedDay={null}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectDay={vi.fn()}
        onSelectEvent={vi.fn()}
      />,
    );
    const cell = screen.getAllByRole("gridcell")[0];
    expect(cell.className).not.toContain("border-l");
    expect(cell.className).not.toContain("border-t");
    expect(cell.className).toContain("rounded-[18px]");
    expect(screen.getByRole("grid").className).not.toMatch(/(^| )border( |$)/);
  });

  it("weekday header labels are centred", () => {
    render(
      <MonthCalendarLarge
        events={[]}
        month={month}
        selectedDay={null}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectDay={vi.fn()}
        onSelectEvent={vi.fn()}
      />,
    );
    const fri = screen.getByText("Fri");
    expect(fri.className).toContain("text-center");
  });

  it("shows the month label only on the 1st, not on every first-row cell", () => {
    render(
      <MonthCalendarLarge
        events={[]}
        month={month}
        selectedDay={null}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectDay={vi.fn()}
        onSelectEvent={vi.fn()}
      />,
    );
    expect(screen.getAllByText("Nov")).toHaveLength(1);
  });
});

describe("WeekView brand", () => {
  const weekStart = startOfWeek(parseISO("2026-11-21T00:00:00"), {
    weekStartsOn: 0,
  });
  const events = [ev("w1", "Brunch", NOV_21, NOV_21_END)];

  it("chips have no left rail and the scroll container has no border", () => {
    const { container } = render(
      <WeekView
        weekStart={weekStart}
        events={events}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={vi.fn()}
      />,
    );
    const chip = screen.getByRole("button", { name: /Brunch/ });
    expect(chip.className).not.toContain("border-l");
    expect(chip.className).not.toContain("rounded-md");
    expect(
      chip.querySelector('[aria-hidden="true"].rounded-full'),
    ).not.toBeNull();
    const scroller = container.querySelector(".overflow-y-auto") as HTMLElement;
    expect(scroller.className).not.toMatch(/(^| )border( |$)/);
    expect(scroller.className).toContain("rounded-[22px]");
  });

  it("hour labels are friendly lowercase and hour 0 is labelled", () => {
    render(
      <WeekView
        weekStart={weekStart}
        events={[]}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={vi.fn()}
      />,
    );
    expect(screen.getByText("9 am")).toBeInTheDocument();
    expect(screen.getByText("12 am")).toBeInTheDocument();
    expect(screen.queryByText("9 AM")).toBeNull();
  });
});

describe("ListView brand", () => {
  const events = [ev("l1", "Park day", NOV_21, NOV_21_END)];

  it("rows have no colour border style and use a glass item radius", () => {
    render(
      <ListView
        events={events}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={vi.fn()}
      />,
    );
    const row = screen.getByRole("button", { name: /Park day/ });
    expect(row.style.borderLeftColor).toBe("");
    expect(row.className).toContain("glass-item");
    expect(row.className).toContain("rounded-[22px]");
    expect(row.className).not.toContain("border-l");
  });

  it("shows a friendly date and time line", () => {
    render(
      <ListView
        events={events}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={vi.fn()}
      />,
    );
    const d = parseISO(NOV_21);
    expect(
      screen.getByText(`${format(d, "EEE, MMM d")} at 9 am`),
    ).toBeInTheDocument();
  });

  it("month header is plain muted text, not a bordered opaque bar", () => {
    render(
      <ListView
        events={events}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={vi.fn()}
      />,
    );
    const head = screen.getByRole("heading", {
      level: 2,
      name: "November 2026",
    });
    expect(head.className).toContain("sticky");
    expect(head.className).toContain("text-muted");
    expect(head.className).not.toContain("border-b");
    expect(head.className).not.toContain("glass-solid");
  });
});

describe("EventRail brand", () => {
  it("rows use a colour dot instead of a 3px grid rail, headers have no bar", () => {
    const { container } = render(
      <EventRail
        events={[ev("r1", "Quiz", NOV_21, NOV_21_END)]}
        selectedDay={null}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={vi.fn()}
      />,
    );
    const row = screen.getByRole("button", { name: /Quiz/ });
    expect(row.className).not.toContain("grid-cols-[3px_1fr]");
    expect(
      row.querySelector('[aria-hidden="true"].rounded-full'),
    ).not.toBeNull();
    const head = container.querySelector("h3") as HTMLElement;
    expect(head.className).not.toContain("border-b");
    expect(head.className).not.toContain("glass-solid");
  });
});
