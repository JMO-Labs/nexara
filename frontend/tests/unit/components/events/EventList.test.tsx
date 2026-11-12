/**
 * @file tests/unit/components/events/EventList.test.tsx
 * @brief EventList: loading/empty/error states, month grouping, sticky headers.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EventList } from "@/components/events/EventList";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
}));
vi.mock("@/components/events/EventCard", () => ({
  EventCard: ({ event }: any) => <div>{event.title}</div>,
}));
const hook = vi.fn();
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: () => hook(),
}));

const ev = (id: string, title: string, starts_at: string) => ({
  id,
  title,
  starts_at,
  ends_at: starts_at,
});

describe("EventList", () => {
  beforeEach(() => {
    push.mockClear();
    hook.mockReset();
  });

  it("shows busy skeleton list while loading", () => {
    hook.mockReturnValue({ isLoading: true });
    render(<EventList />);
    expect(
      screen.getByRole("status", { name: /loading events/i }),
    ).toBeTruthy();
  });

  it("empty state offers a Create event CTA", async () => {
    hook.mockReturnValue({ isLoading: false, data: { items: [] } });
    render(<EventList />);
    expect(screen.getByText(/no events\. create one/i)).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: /create event/i }),
    );
    expect(push).toHaveBeenCalledWith("/app/events");
  });

  it("error Retry calls refetch", async () => {
    const refetch = vi.fn();
    hook.mockReturnValue({ isLoading: false, error: new Error("x"), refetch });
    render(<EventList />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it("groups by month with sticky headings", () => {
    hook.mockReturnValue({
      isLoading: false,
      data: {
        items: [
          ev("1", "A", "2025-01-10T12:00:00Z"),
          ev("2", "B", "2025-01-20T12:00:00Z"),
          ev("3", "C", "2025-02-05T12:00:00Z"),
        ],
      },
    });
    render(<EventList />);
    const heads = screen.getAllByRole("heading", { level: 3 });
    expect(heads).toHaveLength(2);
    expect(heads[0].className).toContain("sticky");
  });
});
