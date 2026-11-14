/**
 * @file tests/unit/components/home/HomeFeed.test.tsx
 * @brief HomeFeed rendering, new-items pill, infinite scroll sentinel.
 */
import { render as rtlRender, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { FeedItem } from "@/lib/api/home";

const state = vi.hoisted(() => ({
  hook: {} as Record<string, unknown>,
  io: null as null | ((entries: IntersectionObserverEntry[]) => void),
}));
vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({ data: [] }),
}));
vi.mock("@/hooks/useHomeFeed", () => ({ useHomeFeed: () => state.hook }));
vi.mock("@/components/feed/PostComposer", () => ({
  PostComposer: () => <div contentEditable suppressContentEditableWarning />,
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: ({ post }: { post: { id: string } }) => <div>post {post.id}</div>,
}));
vi.mock("@/components/feed/KudosComposer", () => ({
  KudosComposer: () => <div role="dialog" aria-label="Send Kudos" />,
}));
vi.mock("@/components/feed/ActivityLine", () => ({
  ActivityLine: ({ item }: { item: { id: string } }) => (
    <div>activity {item.id}</div>
  ),
}));

import { HomeFeed } from "@/components/home/HomeFeed";

const render = (ui: React.ReactElement) =>
  rtlRender(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  );

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
    expect(screen.getByText("No posts yet")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Create your first post" }),
    ).toBeTruthy();
  });

  it("loading shows staggered skeletons, no empty state", () => {
    state.hook.items = [];
    state.hook.isLoading = true;
    render(<HomeFeed />);
    expect(screen.getAllByTestId("feed-skeleton").length).toBe(3);
    const status = screen.getByRole("status", { name: "Loading feed" });
    expect(status.querySelectorAll('[role="status"]')).toHaveLength(0);
    expect(
      screen
        .getAllByTestId("feed-skeleton")
        .every((e) => e.getAttribute("aria-hidden") === "true"),
    ).toBe(true);
    expect(screen.queryByText("No posts yet")).toBeNull();
  });

  it("error shows retry", () => {
    const refetch = vi.fn();
    state.hook.items = [];
    state.hook.isError = true;
    state.hook.refetch = refetch;
    render(<HomeFeed />);
    expect(screen.getByText("Failed to load feed")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalled();
    expect(screen.queryByText("No posts yet")).toBeNull();
  });

  it("uses 8px item gap", () => {
    const { container } = render(<HomeFeed />);
    expect(container.querySelector("ul")?.className).toContain("gap-2");
  });

  it("skeletons use the same Card surface and padding as PostCard", () => {
    state.hook.items = [];
    state.hook.isLoading = true;
    render(<HomeFeed />);
    for (const e of screen.getAllByTestId("feed-skeleton")) {
      expect(e.className).toContain("bg-surface");
      expect(e.className).toContain("p-3");
      expect(e.className).toContain("md:p-4");
    }
  });

  it("skips stagger fade-in under reduced motion", () => {
    const mm = window.matchMedia;
    window.matchMedia = ((q: string) => ({
      matches: true,
      media: q,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    })) as unknown as typeof window.matchMedia;
    state.hook.items = [];
    state.hook.isLoading = true;
    render(<HomeFeed />);
    window.matchMedia = mm;
    for (const e of screen.getAllByTestId("feed-skeleton"))
      expect((e as HTMLElement).style.opacity).not.toBe("0");
  });

  it("staggers skeletons with per-item delay", () => {
    state.hook.items = [];
    state.hook.isLoading = true;
    render(<HomeFeed />);
    const delays = screen
      .getAllByTestId("feed-skeleton")
      .map((e) => e.getAttribute("data-delay"));
    expect(delays).toEqual(["0", "0.08", "0.16"]);
  });

  it("uses shared radius token, not arbitrary values", () => {
    const { container } = render(<HomeFeed />);
    expect(container.innerHTML).not.toContain("rounded-[");
  });
});

describe("HomeFeed kudos action", () => {
  it("opens the Send Kudos dialog from the feed button", () => {
    render(<HomeFeed />);
    expect(screen.queryByRole("dialog", { name: "Send Kudos" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Send Kudos" }));
    expect(
      screen.getByRole("dialog", { name: "Send Kudos" }),
    ).toBeInTheDocument();
  });
});
