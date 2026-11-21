/**
 * @file tests/unit/home/tiles/FeedTile.test.tsx
 * @brief FeedTile: scope filtering, empty states, summary count, link,
 *        feed filter pills (All / Kudos / Prompts) driven by ?feed=.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
const nav = vi.hoisted(() => ({
  replace: vi.fn(),
  params: new URLSearchParams(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: nav.replace }),
  usePathname: () => "/app",
  useSearchParams: () => nav.params,
}));
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { FeedItem } from "@/lib/api/home";

const state = vi.hoisted(() => ({ hook: {} as Record<string, unknown> }));
vi.mock("@/hooks/useHomeFeed", () => ({ useHomeFeed: () => state.hook }));
vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({ data: [] }),
}));
vi.mock("@/hooks/useHomeSummary", () => ({
  useHomeSummary: () => ({ data: { new_posts: 4 } }),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({
    data: [
      { id: "a", name: "Book club" },
      { id: "b", name: "Soccer" },
    ],
  }),
}));
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/components/feed/PostComposer", () => ({
  PostComposer: () => <div contentEditable suppressContentEditableWarning />,
}));
vi.mock("@/components/feed/KudosComposer", () => ({
  KudosComposer: () => null,
}));
vi.mock("@/components/feed/KudosWall", () => ({
  KudosWall: (p: { embedded?: boolean }) => (
    <div>kudos wall {p.embedded ? "embedded" : "page"}</div>
  ),
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: ({ post }: { post: { id: string } }) => <div>post {post.id}</div>,
}));
vi.mock("@/components/feed/ActivityLine", () => ({
  ActivityLine: ({ item }: { item: { id: string } }) => (
    <div>activity {item.id}</div>
  ),
}));

import { FeedTile } from "@/components/home/tiles/FeedTile";
import { useHomeScope } from "@/stores/homeScope";

const post = (id: string, sg: string | null, extra = {}) =>
  ({
    kind: "post",
    id,
    created_at: "t",
    post: { id, subgroup_id: sg, ...extra },
  }) as unknown as FeedItem;
const act = (id: string) =>
  ({ kind: "activity", id, created_at: "t", activity: { id } }) as FeedItem;

beforeEach(() => {
  nav.replace.mockClear();
  nav.params = new URLSearchParams();
  useHomeScope.setState({ scope: "all" });
  state.hook = {
    items: [post("pa", "a"), post("pb", "b"), act("x")],
    pending: [],
    freshIds: new Set<string>(),
    reveal: vi.fn(),
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isLoading: false,
  };
});

const ui = () => <FeedTile open onToggle={() => {}} />;

describe("FeedTile", () => {
  it("shows everything at scope all", () => {
    render(ui());
    expect(screen.getByText("post pa")).toBeTruthy();
    expect(screen.getByText("post pb")).toBeTruthy();
    expect(screen.getByText("activity x")).toBeTruthy();
  });

  it("filters other groups and activity when a group is selected", () => {
    useHomeScope.setState({ scope: "a" });
    render(ui());
    expect(screen.getByText("post pa")).toBeTruthy();
    expect(screen.queryByText("post pb")).toBeNull();
    expect(screen.queryByText("activity x")).toBeNull();
  });

  it("shows a group-named empty state when scope has no posts", () => {
    useHomeScope.setState({ scope: "b" });
    state.hook.items = [post("pa", "a")];
    render(ui());
    expect(screen.getByText("Nothing from Soccer yet")).toBeTruthy();
  });

  it("summary and count use new_posts", () => {
    render(ui());
    expect(screen.getByText("4 new posts")).toBeTruthy();
    expect(screen.getByLabelText("4 new")).toBeTruthy();
  });

  it("links to the feed", () => {
    render(ui());
    expect(
      screen.getByRole("link", { name: "Open feed" }).getAttribute("href"),
    ).toBe("/app#feed");
  });

  it("scrolls inside the tile at md+ and keeps the grid area", () => {
    const { container } = render(ui());
    expect(container.querySelector("section")?.className).toContain(
      "md:[grid-area:feed]",
    );
    expect(container.querySelector("[data-feed-scroll]")?.className).toContain(
      "md:overflow-y-auto",
    );
  });

  it("empty with zero items and all scope keeps the create action", () => {
    state.hook.items = [];
    render(ui());
    expect(
      screen.getByRole("button", { name: "Create your first post" }),
    ).toBeTruthy();
  });

  it("shows All / Kudos / Prompts pills, All selected by default", () => {
    render(ui());
    const group = screen.getByRole("radiogroup", { name: "Feed filter" });
    expect(group).toBeTruthy();
    expect(
      screen.getByRole("radio", { name: "All" }).getAttribute("aria-checked"),
    ).toBe("true");
    expect(screen.getByRole("radio", { name: "Kudos" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Prompts" })).toBeTruthy();
  });

  it("?feed=kudos renders the embedded KudosWall, not the feed", () => {
    nav.params = new URLSearchParams("feed=kudos");
    render(ui());
    expect(screen.getByText("kudos wall embedded")).toBeTruthy();
    expect(screen.queryByText("post pa")).toBeNull();
    expect(screen.queryByText("activity x")).toBeNull();
    expect(
      screen.getByRole("radio", { name: "Kudos" }).getAttribute("aria-checked"),
    ).toBe("true");
  });

  it("?feed=prompts keeps only prompt replies and posts (drops normal posts and activity)", () => {
    nav.params = new URLSearchParams("feed=prompts");
    state.hook.items = [
      post("reply", null, { reply_to_prompt_id: "p1" }),
      post("prompt", null, { is_prompt_post: true }),
      post("normal", null),
      act("x"),
    ];
    render(ui());
    expect(screen.getByText("post reply")).toBeTruthy();
    expect(screen.getByText("post prompt")).toBeTruthy();
    expect(screen.queryByText("post normal")).toBeNull();
    expect(screen.queryByText("activity x")).toBeNull();
  });

  it("clicking Kudos replaces the URL with feed=kudos, keeping other params", async () => {
    nav.params = new URLSearchParams("tile=photos");
    render(ui());
    await userEvent.click(screen.getByRole("radio", { name: "Kudos" }));
    expect(nav.replace).toHaveBeenCalledWith("/app?tile=photos&feed=kudos", {
      scroll: false,
    });
  });

  it("clicking All removes the feed param", async () => {
    nav.params = new URLSearchParams("feed=kudos");
    render(ui());
    await userEvent.click(screen.getByRole("radio", { name: "All" }));
    expect(nav.replace).toHaveBeenCalledWith("/app", { scroll: false });
  });
});
