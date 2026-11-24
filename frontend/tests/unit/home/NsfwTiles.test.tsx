/**
 * @file tests/unit/home/NsfwTiles.test.tsx
 * @brief NSFW covers on Slideshow and home photo tiles.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Slideshow, SLIDE_MS } from "@/components/galleries/Slideshow";
import { PhotosTile } from "@/components/home/tiles/PhotosTile";
import { OnThisDayTile } from "@/components/home/tiles/OnThisDayTile";
import { resetRevealed } from "@/components/feed/NsfwCover";

const h = vi.hoisted(() => ({
  always: false,
  items: [] as unknown[],
}));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: { always_show_nsfw: h.always } }),
}));
vi.mock("@/hooks/useMembers", () => ({
  useMemberProfile: () => ({ data: undefined }),
}));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => true }));
vi.mock("@/lib/api/memories", () => ({
  getOnThisDay: async () => ({
    items: [
      {
        id: "p1",
        content: "x",
        author: { display_name: "A" },
        media: [{ mime_type: "image/png", url: "u", thumbnail_url: null }],
        is_nsfw: true,
      },
      { id: "p2", content: "y", author: { display_name: "B" }, media: [] },
    ],
    years_ago: [1, 1],
  }),
}));
vi.mock("@/hooks/useHomeMedia", () => ({
  useHomeMedia: () => ({ data: { items: h.items } }),
}));
vi.mock("@/components/home/HomeTile", () => ({
  HomeTile: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );
const item = (id: string, is_nsfw?: boolean) => ({
  id,
  gallery_id: "g",
  media_id: `m${id}`,
  added_by: "u",
  caption: null,
  position: 0,
  created_at: "",
  is_nsfw,
});

beforeEach(() => {
  h.always = false;
  resetRevealed();
});
afterEach(() => vi.useRealTimers());

describe("Slideshow NSFW", () => {
  it("covers, does not mount the image, and pauses until revealed", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    wrap(<Slideshow items={[item("1", true), item("2")] as never} />);
    expect(screen.queryByRole("img")).toBeNull();
    await act(async () => {
      vi.advanceTimersByTime(SLIDE_MS + 100);
    });
    expect(
      screen.getByRole("button", { name: "Show NSFW content" }),
    ).toBeInTheDocument();
    await act(async () => {
      screen.getByRole("button", { name: "Show NSFW content" }).click();
    });
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("covers when the whole gallery is NSFW, not when always_show", () => {
    const { unmount } = wrap(<Slideshow items={[item("1")] as never} nsfw />);
    expect(
      screen.getByRole("button", { name: "Show NSFW content" }),
    ).toBeInTheDocument();
    unmount();
    h.always = true;
    wrap(<Slideshow items={[item("1")] as never} nsfw />);
    expect(
      screen.queryByRole("button", { name: "Show NSFW content" }),
    ).toBeNull();
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});

describe("PhotosTile NSFW", () => {
  it("shows a compact cover for NSFW media", async () => {
    const m = (id: string, is_nsfw: boolean) => ({
      media_id: id,
      media: { id, alt_text: null, is_nsfw },
    });
    h.items = [m("a", true), m("b", false)];
    wrap(<PhotosTile open onToggle={() => {}} />);
    const btn = screen.getByRole("button", { name: "Show NSFW content" });
    expect(btn).toHaveTextContent("NSFW");
    await userEvent.click(btn);
    expect(
      screen.queryByRole("button", { name: "Show NSFW content" }),
    ).toBeNull();
  });
});

describe("OnThisDayTile NSFW", () => {
  it("covers NSFW posts only", async () => {
    wrap(<OnThisDayTile open onToggle={() => {}} />);
    expect(
      await screen.findAllByRole("button", { name: "Show NSFW content" }),
    ).toHaveLength(1);
    expect(screen.getByText("B")).toBeInTheDocument();
  });
});
