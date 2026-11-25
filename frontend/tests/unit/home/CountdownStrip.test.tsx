/**
 * @file tests/unit/home/CountdownStrip.test.tsx
 * @brief Home countdown strip: hidden when empty, capped at 6, See all link.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const state = { data: [] as unknown[] };
vi.mock("@/hooks/useCountdowns", () => ({ useFollowing: () => state }));
import { CountdownStrip } from "@/components/home/CountdownStrip";

const mk = (i: number, days: number, server = true) => {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const p = (n: number) => String(n).padStart(2, "0");
  return {
    id: `c${i}`,
    title: `T${i}`,
    emoji: "🎉",
    next_date: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`,
    ...(server ? { days_left: days } : {}),
  };
};

describe("CountdownStrip", () => {
  it("renders nothing when following none", () => {
    state.data = [];
    const { container } = render(<CountdownStrip />);
    expect(container).toBeEmptyDOMElement();
  });
  it("sorts soonest first, shows 12d, Today!", () => {
    state.data = [mk(2, 12), mk(1, 0)];
    render(<CountdownStrip />);
    const links = screen.getAllByTestId("countdown-chip");
    expect(links[0]).toHaveTextContent("Today!");
    expect(links[1]).toHaveTextContent("12d");
    expect(links[1]).toHaveTextContent("T2");
    expect(links[1]).toHaveAttribute("href", "/app/countdowns/c2");
  });
  it("lists upcoming before ended, and prefers server days_left", () => {
    state.data = [mk(1, -2), mk(2, 5), { ...mk(3, 9), days_left: 0 }];
    render(<CountdownStrip />);
    const chips = screen.getAllByTestId("countdown-chip");
    expect(chips.map((c) => c.getAttribute("href"))).toEqual([
      "/app/countdowns/c3",
      "/app/countdowns/c2",
      "/app/countdowns/c1",
    ]);
    expect(chips[0]).toHaveTextContent("Today!");
    expect(chips[1]).toHaveAttribute("aria-label", "5 days until T2");
    expect(chips[2]).toHaveTextContent("2d ago");
  });
  it("falls back to the browser clock without days_left", () => {
    state.data = [mk(1, 3, false)];
    render(<CountdownStrip />);
    expect(screen.getByTestId("countdown-chip")).toHaveTextContent("3d");
  });
  it("shows at most 6 and a See all link", () => {
    state.data = Array.from({ length: 7 }, (_, i) => mk(i, i + 1));
    render(<CountdownStrip />);
    expect(screen.getAllByTestId("countdown-chip")).toHaveLength(6);
    expect(screen.queryByText("T6")).toBeNull();
    expect(screen.getByRole("link", { name: /see all/i })).toHaveAttribute(
      "href",
      "/app/countdowns",
    );
  });
});
