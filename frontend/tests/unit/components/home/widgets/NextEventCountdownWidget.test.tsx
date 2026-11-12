/**
 * @file tests/unit/components/home/widgets/NextEventCountdownWidget.test.tsx
 * @brief Unit tests for NextEventCountdownWidget (event and empty states).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: vi.fn(),
}));
vi.mock("@/components/events/EventCountdown", () => ({
  EventCountdown: ({ event }: { event: { title: string } }) => (
    <div data-testid="countdown">{event.title}</div>
  ),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { NextEventCountdownWidget } from "@/components/home/widgets/NextEventCountdownWidget";
import { useUpcomingEvents } from "@/hooks/useEvents";

const mockHook = (value: unknown) =>
  vi.mocked(useUpcomingEvents).mockReturnValue(value as never);

describe("NextEventCountdownWidget", () => {
  it("shows countdown linked to the first event", () => {
    mockHook({
      data: {
        items: [
          { id: "e1", title: "Picnic" },
          { id: "e2", title: "B" },
        ],
      },
      isLoading: false,
    });
    render(<NextEventCountdownWidget />);
    expect(screen.getByTestId("countdown")).toHaveTextContent("Picnic");
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/app/events?event=e1",
    );
  });

  it("shows empty state when no events", () => {
    mockHook({ data: { items: [] }, isLoading: false });
    render(<NextEventCountdownWidget />);
    expect(screen.getByText("No upcoming events")).toBeInTheDocument();
    expect(screen.queryByTestId("countdown")).toBeNull();
  });
});
