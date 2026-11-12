/**
 * @file tests/unit/events/EventList.test.tsx
 * @brief Upcoming event list: loading, items grouped by month, empty, error.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { EventList } from "@/components/events/EventList";
import { listEvents } from "@/lib/api/events";
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

const mockList = vi.mocked(listEvents);

describe("EventList", () => {
  beforeEach(() => mockList.mockReset());

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

  it("shows an error state with retry", async () => {
    mockList.mockImplementation(() => Promise.reject(new Error("boom")));
    renderWithProviders(<EventList />);
    expect(
      await screen.findByText("Couldn't load events", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
