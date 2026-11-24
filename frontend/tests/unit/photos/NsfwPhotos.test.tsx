/**
 * @file tests/unit/photos/NsfwPhotos.test.tsx
 * @brief NSFW covers on photo grids and the uploader tile button gating.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PhotoGrid } from "@/components/galleries/PhotoGrid";
import { AllPhotos } from "@/components/photos/AllPhotos";
import { GalleryDrawer } from "@/components/galleries/galleries-page/GalleryDrawer";
import { resetRevealed } from "@/components/feed/NsfwCover";
import { useSession } from "@/stores/session";

const h = vi.hoisted(() => ({
  always: false,
  feature: true,
  item: {} as Record<string, unknown>,
}));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: { always_show_nsfw: h.always } }),
}));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => h.feature }));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: () => <span />,
}));
vi.mock("@/components/galleries/Lightbox", () => ({ Lightbox: () => null }));
vi.mock("@/components/galleries/GalleryUpload", () => ({
  GalleryUpload: () => null,
}));
vi.mock("@/hooks/useGroupMod", () => ({ useIsGroupMod: () => false }));
vi.mock("@/hooks/useNsfw", () => ({
  useSetGalleryNsfw: () => ({ mutate: vi.fn() }),
  useSetMediaNsfw: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/hooks/useEvents", () => ({
  useEventDetail: () => ({ data: undefined }),
}));
vi.mock("@/hooks/useMembers", () => ({
  useMemberProfile: () => ({ data: { display_name: "O" } }),
}));
vi.mock("@/hooks/useGalleries", () => {
  const mut = () => ({ mutate: vi.fn(), isPending: false });
  return {
    useGalleryDetail: () => ({
      data: {
        id: "g1",
        title: "G",
        owner_id: "x",
        contribution_policy: "owner_only",
      },
    }),
    useGalleryItems: () => ({
      data: [
        {
          id: "i1",
          media_id: "m1",
          added_by: "me",
          caption: null,
          is_nsfw: false,
          ...h.item,
        },
      ],
      isLoading: false,
    }),
    useUpdateGallery: mut,
    useDeleteGallery: mut,
    useRemoveItem: mut,
  };
});

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );

beforeEach(() => {
  h.always = false;
  h.feature = true;
  h.item = {};
  resetRevealed();
  useSession.setState({
    user: { id: "me", role: "member", age_group: "adult" } as never,
  });
});

describe("PhotoGrid", () => {
  it("covers NSFW ids until revealed", async () => {
    wrap(<PhotoGrid mediaIds={["a", "b"]} nsfwIds={["a"]} />);
    expect(
      screen.getAllByRole("button", { name: "Show NSFW content" }),
    ).toHaveLength(1);
    await userEvent.click(
      screen.getByRole("button", { name: "Show NSFW content" }),
    );
    expect(
      screen.queryByRole("button", { name: "Show NSFW content" }),
    ).toBeNull();
  });
  it("honours always_show_nsfw", () => {
    h.always = true;
    wrap(<PhotoGrid mediaIds={["a"]} nsfwIds={["a"]} />);
    expect(
      screen.queryByRole("button", { name: "Show NSFW content" }),
    ).toBeNull();
  });
});

describe("AllPhotos", () => {
  it("covers items whose media is_nsfw", () => {
    const it = (id: string, is_nsfw: boolean) => ({
      media_id: id,
      media: {
        id,
        alt_text: null,
        is_nsfw,
        created_at: "2026-01-01T00:00:00Z",
      },
      source: "post",
      source_id: "s",
      source_title: null,
      created_at: "2026-01-01T00:00:00Z",
    });
    wrap(
      <AllPhotos
        items={[it("a", true), it("b", false)] as never}
        isLoading={false}
        error={null}
        onOpen={() => {}}
      />,
    );
    expect(
      screen.getAllByRole("button", { name: "Show NSFW content" }),
    ).toHaveLength(1);
  });
});

describe("uploader tile NSFW button", () => {
  const open = () =>
    wrap(
      <GalleryDrawer galleryId="g1" onClose={() => {}} onOpenItem={() => {}} />,
    );
  it("shows for adults with the feature on", () => {
    open();
    expect(
      screen.getByRole("button", { name: "Mark photo NSFW" }),
    ).toHaveTextContent("NSFW");
  });
  it("is hidden when the feature is off", () => {
    h.feature = false;
    open();
    expect(
      screen.queryByRole("button", { name: "Mark photo NSFW" }),
    ).toBeNull();
  });
  it("is disabled with the moderator note when a lock applies", () => {
    h.item = { is_nsfw: true, is_nsfw_own: false, nsfw_locked: true };
    open();
    const btn = screen.getByRole("button", {
      name: "A moderator marked this NSFW.",
    });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-pressed", "false");
  });
  it("shows only the own flag, not an inherited album flag", () => {
    h.item = { is_nsfw: true, is_nsfw_own: false, nsfw_locked: false };
    open();
    expect(
      screen.getByRole("button", { name: "Mark photo NSFW" }),
    ).toHaveAttribute("aria-pressed", "false");
  });
});
