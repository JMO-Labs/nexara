/**
 * @file tests/unit/components/home/NextUpCard.test.tsx
 * @brief NextUpCard selection rules.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

let items: unknown[] = [];
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: () => ({ data: { items }, isLoading: false }),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

import { NextUpCard } from "@/components/home/NextUpCard";

const ev = (id: string, title: string, day: number, rsvp: string | null) => ({
  id,
  title,
  location: "Park",
  starts_at: `2030-01-${String(day).padStart(2, "0")}T18:00:00Z`,
  rsvp_counts: { attending: 3 },
  user_rsvp: rsvp ? { status: rsvp } : null,
});

beforeEach(() => {
  items = [];
});

describe("NextUpCard", () => {
  it("prefers the nearest event the viewer RSVP'd to", () => {
    items = [
      ev("a", "Near", 5, null),
      ev("b", "Mine", 9, "attending"),
      ev("c", "Maybe", 7, "maybe"),
    ];
    render(<NextUpCard />);
    expect(screen.getByText("Maybe")).toBeInTheDocument();
    expect(screen.queryByText("Near")).toBeNull();
    expect(screen.getByText(/3 going/)).toBeInTheDocument();
  });

  it("falls back to the nearest upcoming event", () => {
    items = [ev("b", "Later", 9, "declined"), ev("a", "Near", 5, null)];
    render(<NextUpCard />);
    expect(screen.getByText("Near")).toBeInTheDocument();
  });

  it("renders nothing without events", () => {
    const { container } = render(<NextUpCard />);
    expect(container).toBeEmptyDOMElement();
  });
});
