/**
 * @file tests/unit/events/EventPage.test.tsx
 * @brief EventPage: loaded, loading and not-found states.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventPage } from "@/components/events/EventPage";
import { ApiError } from "@/lib/api/errors";

const useEventDetail = vi.fn();
vi.mock("@/hooks/useEvents", () => ({
  useEventDetail: (id: string) => useEventDetail(id),
}));
vi.mock("@/components/events/event-detail/EventDetailBody", () => ({
  EventDetailBody: ({ event }: { event: { title: string } }) => (
    <div data-testid="body">{event.title}</div>
  ),
}));
vi.mock("@/components/events/EventCountdown", () => ({
  EventCountdown: () => <div data-testid="countdown" />,
}));

const future = new Date(Date.now() + 86400_000 * 2).toISOString();
const past = new Date(Date.now() - 86400_000 * 2).toISOString();
const ev = (starts_at: string) => ({ id: "e1", title: "Picnic", starts_at });

describe("EventPage", () => {
  beforeEach(() => useEventDetail.mockReset());

  it("shows skeleton while loading", () => {
    useEventDetail.mockReturnValue({ isLoading: true });
    render(<EventPage id="e1" />);
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
    expect(screen.queryByTestId("body")).toBeNull();
  });

  it("renders body, countdown and back link when loaded", () => {
    useEventDetail.mockReturnValue({ data: ev(future) });
    render(<EventPage id="e1" />);
    expect(screen.getByTestId("body").textContent).toBe("Picnic");
    expect(screen.getByTestId("countdown")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /back/i }).getAttribute("href"),
    ).toBe("/app/events");
  });

  it("omits countdown for past events", () => {
    useEventDetail.mockReturnValue({ data: ev(past) });
    render(<EventPage id="e1" />);
    expect(screen.queryByTestId("countdown")).toBeNull();
  });

  it("shows not found on 404", () => {
    useEventDetail.mockReturnValue({
      error: new ApiError(404, "not_found", "nope"),
    });
    render(<EventPage id="e1" />);
    expect(screen.getByText("Event not found")).toBeTruthy();
    expect(screen.getByRole("link", { name: /back/i })).toBeTruthy();
  });

  it("does not render its own main landmark (Shell provides it)", () => {
    useEventDetail.mockReturnValue({ data: ev(future) });
    render(<EventPage id="e1" />);
    expect(screen.queryByRole("main")).toBeNull();
  });
});
