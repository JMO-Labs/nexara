/**
 * @file tests/unit/feed/NsfwModeration.test.tsx
 * @brief NSFW moderation menu, album cover reveal, privacy row, locked toggle.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PostCard } from "@/components/feed/PostCard";
import { AlbumGrid } from "@/components/photos/AlbumGrid";
import { PrivacyTab } from "@/components/settings/PrivacyTab";
import { NsfwToggle } from "@/components/compose/NsfwToggle";
import { resetRevealed } from "@/components/feed/NsfwCover";
import { useSession } from "@/stores/session";
import type { Post } from "@/lib/api/posts";
import type { Gallery } from "@/lib/api/galleries";

const h = vi.hoisted(() => ({
  groupMod: false,
  always: false,
  mutate: vi.fn(),
}));
vi.mock("@/hooks/useGroupMod", () => ({ useIsGroupMod: () => h.groupMod }));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => true }));
vi.mock("@/hooks/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("@/hooks/usePosts", () => ({
  useDeletePost: () => ({ mutate: vi.fn() }),
  useTogglePostReaction: () => ({ mutate: vi.fn() }),
  useSetPostNsfw: () => ({ mutate: h.mutate }),
}));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({
    data: {
      profile_visible_to: "community",
      show_birthday_to: "nobody",
      always_show_nsfw: h.always,
    },
  }),
  useUpdateSettings: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("@/components/feed/CommentThread", () => ({
  CommentThread: () => null,
}));
vi.mock("@/components/feed/BookmarkButton", () => ({
  BookmarkButton: () => null,
}));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: () => <span />,
}));

const post = {
  id: "p1",
  content: "hi",
  author: { id: "other", username: "o", display_name: "O", avatar_url: null },
  media: [],
  poll: null,
  reactions: [],
  comment_count: 0,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  subgroup_id: "g1",
  subgroup_name: null,
  subgroup_slug: null,
} as unknown as Post;

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );
const as = (role: string, age_group = "adult") =>
  useSession.setState({ user: { id: "me", role, age_group } as never });

beforeEach(() => {
  h.groupMod = false;
  h.always = false;
  h.mutate.mockClear();
  resetRevealed();
});

async function openMenu() {
  await userEvent.click(screen.getByRole("button", { name: "Post options" }));
}

describe("post NSFW moderation menu", () => {
  it("admin sees Mark NSFW and it mutates", async () => {
    as("admin");
    wrap(<PostCard post={post} />);
    await openMenu();
    await userEvent.click(
      await screen.findByRole("menuitem", { name: "Mark NSFW" }),
    );
    expect(h.mutate).toHaveBeenCalledWith({ id: "p1", value: true });
  });

  it("group moderator sees Remove NSFW on an NSFW post", async () => {
    as("member");
    h.groupMod = true;
    wrap(<PostCard post={{ ...post, is_nsfw: true }} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Show NSFW content" }),
    );
    await openMenu();
    expect(
      await screen.findByRole("menuitem", { name: "Remove NSFW" }),
    ).toBeInTheDocument();
  });

  it("plain member has no NSFW item", async () => {
    as("member");
    wrap(<PostCard post={post} />);
    await openMenu();
    await screen.findByRole("menuitem", { name: "Report" });
    expect(screen.queryByRole("menuitem", { name: /NSFW/ })).toBeNull();
  });
});

describe("AlbumGrid NSFW cover", () => {
  const g = {
    id: "1",
    owner_id: "u",
    title: "Album 1",
    description: null,
    cover_media_id: "m",
    item_count: 2,
    is_nsfw: true,
  } as unknown as Gallery;

  it("covers until revealed, then the card is usable", async () => {
    as("member");
    const onSelect = vi.fn();
    wrap(<AlbumGrid items={[g]} onSelect={onSelect} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Show NSFW content" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Album 1" }));
    expect(onSelect).toHaveBeenCalledWith("1");
  });

  it("skips the cover with always_show_nsfw", () => {
    h.always = true;
    wrap(<AlbumGrid items={[g]} onSelect={() => {}} />);
    expect(
      screen.queryByRole("button", { name: "Show NSFW content" }),
    ).toBeNull();
  });
});

describe("PrivacyTab always_show_nsfw row", () => {
  it("shows for adults only", () => {
    as("member", "adult");
    const { unmount } = wrap(<PrivacyTab />);
    expect(
      screen.getByRole("switch", { name: "Always show NSFW content" }),
    ).toBeInTheDocument();
    unmount();
    as("member", "teen");
    wrap(<PrivacyTab />);
    expect(
      screen.queryByRole("switch", { name: "Always show NSFW content" }),
    ).toBeNull();
  });
});

describe("NsfwToggle locked", () => {
  it("is disabled with the moderator note and linked help", () => {
    as("member");
    wrap(<NsfwToggle checked locked onChange={() => {}} />);
    const sw = screen.getByRole("switch", { name: "NSFW" });
    expect(sw).toBeDisabled();
    expect(sw).toHaveAttribute("aria-describedby");
    expect(
      screen.getByText("A moderator marked this NSFW."),
    ).toBeInTheDocument();
  });
});
