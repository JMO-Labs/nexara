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
  tree: true,
}));
vi.mock("next/navigation", () => ({ usePathname: () => state.path }));
vi.mock("framer-motion", async (orig) => ({
  ...(await orig<typeof import("framer-motion")>()),
  useReducedMotion: () => state.reduced,
}));

vi.mock("@/hooks/useFeature", () => ({ useFeature: () => state.tree }));

import { TopNav } from "@/components/layout/TopNav";

describe("TopNav", () => {
  beforeEach(() => {
    state.dir = "up";
    state.reduced = false;
    state.path = "/app/events";
    state.tree = true;
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

  it("hides Family when the feature is off", () => {
    state.tree = false;
    render(<TopNav />);
    expect(screen.queryByRole("link", { name: "Family" })).toBeNull();
    state.tree = true;
    render(<TopNav />);
    expect(screen.getByRole("link", { name: "Family" })).toHaveAttribute(
      "href",
      "/app/family",
    );
  });
});
