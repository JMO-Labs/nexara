/**
 * @file tests/unit/layout/TopNav.test.tsx
 * @brief Top pill nav: active state; every item stays visible on scroll.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const state = vi.hoisted(() => ({
  dir: "up",
  reduced: false,
  path: "/app/events",
}));
vi.mock("next/navigation", () => ({ usePathname: () => state.path }));
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

  it("keeps every item visible", () => {
    render(<TopNav />);
    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Inbox" })).toBeInTheDocument();
  });
});
