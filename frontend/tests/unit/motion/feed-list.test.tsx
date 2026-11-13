/**
 * @file tests/unit/motion/feed-list.test.tsx
 * @brief HomeFeed items animate layout and respect reduced motion.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});
vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({ data: [] }),
}));
vi.mock("@/hooks/useHomeFeed", () => ({
  useHomeFeed: () => ({
    items: [
      { kind: "post", id: "1", post: { id: "1" } },
      { kind: "post", id: "2", post: { id: "2" } },
    ],
    pending: [],
    reveal: vi.fn(),
    freshIds: new Set(["post:1"]),
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));
vi.mock("@/components/feed/PostComposer", () => ({ PostComposer: () => null }));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: () => <div>post</div>,
}));
vi.mock("@/components/feed/ActivityLine", () => ({ ActivityLine: () => null }));

import { HomeFeed } from "@/components/home/HomeFeed";

beforeEach(() => {
  reduced = false;
});

describe("HomeFeed item motion", () => {
  it("fresh item enters from transparent, others do not animate", () => {
    render(<HomeFeed />);
    const items = screen.getAllByTestId("feed-item");
    expect(items[0]).toHaveStyle({ opacity: "0" });
    // initial={false}: rendered at the final state, no transparent start
    expect(items[1]).toHaveStyle({ opacity: "1" });
  });
  it("skips animation under reduced motion", () => {
    reduced = true;
    render(<HomeFeed />);
    expect(screen.getAllByTestId("feed-item")[0].style.opacity).toBe("");
  });
});
