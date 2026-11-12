/**
 * @file tests/unit/app/home-page.test.tsx
 * @brief Home page: greeting, NextUp, feed and widget column.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { id: "u1", display_name: "Alice Smith" } }),
}));
vi.mock("@/components/home/HomeFeed", () => ({
  HomeFeed: () => <div data-testid="feed" />,
}));
vi.mock("@/components/home/NextUpCard", () => ({
  NextUpCard: () => <div data-testid="nextup" />,
}));
vi.mock("@/components/home/WidgetColumn", () => ({
  WidgetColumn: () => <aside aria-label="Widgets" />,
}));

import AppHome from "@/app/app/page";

describe("AppHome page", () => {
  it("greets by first name", () => {
    render(<AppHome />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Hi Alice." }),
    ).toBeInTheDocument();
  });

  it("renders next-up, feed and the Widgets aside", () => {
    render(<AppHome />);
    expect(screen.getByTestId("nextup")).toBeInTheDocument();
    expect(screen.getByTestId("feed")).toBeInTheDocument();
    expect(screen.getByLabelText("Widgets")).toBeInTheDocument();
  });
});
