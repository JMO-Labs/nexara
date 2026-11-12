/**
 * @file tests/unit/events/EventList.test.tsx
 * @brief Upcoming event list: loading, items grouped by month, empty, error.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { EventList } from "@/components/events/EventList";
import { listEvents } from "@/lib/api/events";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { makeEvent } from "./fixtures";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/components/events/EventCard", () => ({
  EventCard: ({ event }: { event: { title: string } }) => (
    <div data-testid="card">{event.title}</div>
  ),
}));
vi.mock("@/lib/api/events", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/events")>()),
  listEvents: vi.fn(),
}));

vi.mock("@/hooks/useEvents", async (orig) => {
  const actual = await orig<typeof import("@/hooks/useEvents")>();
  return { ...actual, useUpcomingEvents: vi.fn(actual.useUpcomingEvents) };
});

const mockList = vi.mocked(listEvents);
const mockHook = vi.mocked(useUpcomingEvents);

describe("EventList", () => {
  beforeEach(() => {
    mockList.mockReset();
    // vitest >= 3: mockReset restores the real hook passed to vi.fn().
    mockHook.mockReset();
  });

  it("renders items grouped under month headers", async () => {
    mockList.mockResolvedValue({
      items: [
        makeEvent({ id: "a", title: "Picnic" }),
        makeEvent({
          id: "b",
          title: "Concert",
          starts_at: "2026-06-12T10:00:00",
          ends_at: "2026-06-12T11:00:00",
        }),
      ],
    } as never);
    renderWithProviders(<EventList />);
    expect(await screen.findByText("Picnic")).toBeInTheDocument();
    expect(screen.getByText("Concert")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(2);
  });

  it("shows the empty state when there are no events", async () => {
    mockList.mockResolvedValue({ items: [] } as never);
    renderWithProviders(<EventList />);
    expect(await screen.findByText("No upcoming events")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "View all events" }),
    ).toBeInTheDocument();
  });

  it("shows an error state with retry", () => {
    // Stub the hook's error state directly: a rejected promise flowing
    // through react-query is reported by vitest as an unhandled error.
    mockHook.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("boom"),
    } as never);
    renderWithProviders(<EventList />);
    expect(screen.getByText("Couldn't load events")).toBeInTheDocument();
    expect(screen.getByText("Error: boom")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
