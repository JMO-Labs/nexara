/**
 * @file tests/unit/components/home/HomeFeed.test.tsx
 * @brief HomeFeed rendering, new-items pill, infinite scroll sentinel.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { FeedItem } from "@/lib/api/home";

const state = vi.hoisted(() => ({
  hook: {} as Record<string, unknown>,
  io: null as null | (() => void),
}));
vi.mock("@/hooks/useHomeFeed", () => ({ useHomeFeed: () => state.hook }));
vi.mock("@/components/feed/PostComposer", () => ({
  PostComposer: () => <div contentEditable suppressContentEditableWarning />,
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: ({ post }: { post: { id: string } }) => <div>post {post.id}</div>,
}));
vi.mock("@/components/feed/ActivityLine", () => ({
  ActivityLine: ({ item }: { item: { id: string } }) => (
    <div>activity {item.id}</div>
  ),
}));

import { HomeFeed } from "@/components/home/HomeFeed";

const post = (id: string) =>
  ({ kind: "post", id, created_at: "t", post: { id } }) as unknown as FeedItem;
const act = (id: string) =>
  ({
    kind: "activity",
    id,
    created_at: "t",
    activity: { id },
  }) as unknown as FeedItem;

beforeEach(() => {
  state.io = null;
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(cb: () => void) {
        state.io = cb;
      }
      observe() {}
      disconnect() {}
      unobserve() {}
    },
  );
  state.hook = {
    items: [post("1"), act("2")],
    pending: [],
    freshIds: new Set<string>(),
    reveal: vi.fn(),
    fetchNextPage: vi.fn(),
    hasNextPage: true,
    isLoading: false,
  };
});

describe("HomeFeed", () => {
  it("renders mixed items in order", () => {
    render(<HomeFeed />);
    const t = screen
      .getAllByText(/^(post|activity) /)
      .map((e) => e.textContent);
    expect(t).toEqual(["post 1", "activity 2"]);
  });

  it("shows pill and reveals on click", () => {
    state.hook.pending = [act("3"), act("4")];
    render(<HomeFeed />);
    fireEvent.click(screen.getByRole("button", { name: "2 new" }));
    expect(window.scrollTo).toHaveBeenCalled();
    expect(state.hook.reveal).toHaveBeenCalled();
  });

  it("no pill without pending", () => {
    render(<HomeFeed />);
    expect(screen.queryByText(/new$/)).toBeNull();
  });

  it("marks fresh items", () => {
    state.hook.freshIds = new Set(["activity:2"]);
    const { container } = render(<HomeFeed />);
    expect(container.querySelectorAll('[data-new="true"]')).toHaveLength(1);
  });

  it("sentinel fetches next page", () => {
    render(<HomeFeed />);
    state.io?.([{ isIntersecting: true }] as never);
    expect(state.hook.fetchNextPage).toHaveBeenCalled();
  });

  it("empty state", () => {
    state.hook.items = [];
    render(<HomeFeed />);
    expect(screen.getByText("Nothing here yet")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Write the first post" }),
    ).toBeTruthy();
  });
});
