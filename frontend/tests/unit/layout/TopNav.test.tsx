/**
 * @file tests/unit/layout/TopNav.test.tsx
 * @brief Top pill nav: active state, compaction on scroll, reduced motion.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const state = vi.hoisted(() => ({
  dir: "up",
  reduced: false,
  path: "/app/events",
}));
vi.mock("next/navigation", () => ({ usePathname: () => state.path }));
vi.mock("@/hooks/useScrollDirection", () => ({
  useScrollDirection: () => state.dir,
}));
vi.mock("framer-motion", async (orig) => ({
  ...(await orig<typeof import("framer-motion")>()),
  useReducedMotion: () => state.reduced,
}));

import { TopNav } from "@/components/layout/TopNav";

describe("TopNav", () => {
  beforeEach(() => {
    state.dir = "up";
    state.reduced = false;
    state.path = "/app/events";
  });

  it("keeps Community active on legacy member routes", () => {
    state.path = "/app/members/u1";
    render(<TopNav />);
    expect(screen.getByRole("link", { name: "Community" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("marks the current route", () => {
    render(<TopNav />);
    expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("compacts on scroll down and restores on scroll up", () => {
    state.dir = "down";
    const { rerender } = render(<TopNav />);
    expect(screen.getByRole("navigation", { name: "Main" })).toHaveAttribute(
      "data-compact",
      "true",
    );
    state.dir = "up";
    rerender(<TopNav />);
    expect(
      screen.getByRole("navigation", { name: "Main" }),
    ).not.toHaveAttribute("data-compact");
  });

  it("never compacts with reduced motion", () => {
    state.dir = "down";
    state.reduced = true;
    render(<TopNav />);
    expect(
      screen.getByRole("navigation", { name: "Main" }),
    ).not.toHaveAttribute("data-compact");
  });
});
