/**
 * @file tests/unit/components/events/EventsPage.test.tsx
 * @brief Calendar page chrome: PageHeader, New event pill, no masthead.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventsPage } from "@/components/events/events-page/EventsPage";

const st = vi.hoisted(() => ({ view: "month" as string }));
vi.mock("@/components/events/events-page/useEventsPageState", () => ({
  useEventsPageState: () => ({
    view: st.view,
    setView: vi.fn(),
    month: new Date(2026, 4, 1),
    setMonth: vi.fn(),
    weekStart: new Date(2026, 4, 3),
    setWeekStart: vi.fn(),
    selectedDay: null,
    setSelectedDay: vi.fn(),
    selectedEventId: null,
    setSelectedEventId: vi.fn(),
    selectedSources: [],
    setSelectedSources: vi.fn(),
    calendarList: [],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
    filtered: [],
    subgroupNames: new Map(),
    railEvents: [],
    upcoming: [],
    selectedEvent: null,
    onSelectDay: vi.fn(),
    onSelectEvent: vi.fn(),
  }),
}));
vi.mock("@/components/events/events-page/EventsViewPane", () => ({
  EventsViewPane: () => <div>view-pane</div>,
}));
vi.mock("@/components/events/events-page/EventsSidePanel", () => ({
  EventsSidePanel: () => <aside>side</aside>,
}));
vi.mock("@/components/events/CalendarFilterBar", () => ({
  CalendarFilterBar: () => <div>filter-bar</div>,
}));
vi.mock("@/components/events/EventDetailPanel", () => ({
  EventDetailPanel: () => null,
}));
const createModal = vi.fn<(p: { open: boolean }) => null>(() => null);
vi.mock("@/components/events/EventCreateModal", () => ({
  EventCreateModal: (p: { open: boolean }) => createModal(p),
}));

describe("EventsPage", () => {
  it("renders PageHeader Calendar with description, no masthead", () => {
    render(<EventsPage />);
    expect(
      screen.getByRole("heading", { name: "Calendar", level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Everything coming up across your groups"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Events" })).toBeNull();
  });

  it("New event opens the create modal", async () => {
    render(<EventsPage />);
    await userEvent.click(screen.getByRole("button", { name: "New event" }));
    expect(createModal).toHaveBeenCalledWith(
      expect.objectContaining({ open: true }),
    );
  });

  it("puts the calendar in a glass panel", () => {
    render(<EventsPage />);
    const pane = screen.getByText("view-pane").closest(".glass");
    expect(pane).not.toBeNull();
  });

  it("list view: panel hugs content (no forced min-height, items aligned to start)", () => {
    st.view = "list";
    render(<EventsPage />);
    const pane = screen.getByText("view-pane").closest(".glass")!;
    expect(pane.className).not.toContain("min-h-[640px]");
    expect(pane.parentElement).toHaveClass("lg:items-start");
    st.view = "month";
  });
});
