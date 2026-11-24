/**
 * @file tests/unit/galleries/brand-gallery.test.tsx
 * @brief Brand rules for the gallery drawer and uploader: owner display name,
 *        no dashed boxes, glass delete controls, 18px thumbnails.
 */
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { GalleryDrawer } from "@/components/galleries/galleries-page/GalleryDrawer";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { Drawer } from "@/components/ui/Drawer";

const OWNER_ID = "f4ad5dd5-e0d2-4163-bba7-a540fb71aaaa";

const detail = vi.hoisted(() => ({
  current: {} as Record<string, unknown>,
}));

vi.mock("@/hooks/useFeature", () => ({ useFeature: () => false }));
vi.mock("@/hooks/useNsfw", () => ({
  useSetGalleryNsfw: () => ({ mutate: vi.fn() }),
  useSetMediaNsfw: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/hooks/useGroupMod", () => ({ useIsGroupMod: () => false }));
vi.mock("@/hooks/useGalleries", () => {
  const mut = () => ({ mutate: vi.fn(), isPending: false });
  return {
    useGalleryDetail: () => ({ data: detail.current }),
    useGalleryItems: () => ({
      data: [{ id: "i1", media_id: "m1", caption: "Sunset" }],
      isLoading: false,
    }),
    useUpdateGallery: mut,
    useDeleteGallery: mut,
    useRemoveItem: mut,
  };
});
vi.mock("@/hooks/useEvents", () => ({
  useEventDetail: () => ({ data: undefined }),
}));
vi.mock("@/hooks/useMembers", () => ({
  useMemberProfile: () => ({
    data: { id: OWNER_ID, display_name: "Frankie Ortiz", avatar_url: null },
  }),
}));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { id: "someone-else" } }),
}));
vi.mock("@/components/galleries/galleries-page/GalleryCollaborators", () => ({
  GalleryCollaborators: () => null,
}));

describe("GalleryDrawer brand", () => {
  beforeEach(() => {
    detail.current = {
      id: "g1",
      title: "Camping",
      owner_id: OWNER_ID,
      contribution_policy: "owner_only",
      visibility: "private",
    };
  });

  it("shows the owner display name, never the raw owner id", () => {
    render(
      <GalleryDrawer galleryId="g1" onClose={() => {}} onOpenItem={() => {}} />,
    );
    expect(screen.getByText("Frankie Ortiz")).toBeInTheDocument();
    expect(screen.queryByText(OWNER_ID)).toBeNull();
  });

  it("option pills are sentence case", () => {
    render(
      <GalleryDrawer galleryId="g1" onClose={() => {}} onOpenItem={() => {}} />,
    );
    expect(screen.getByRole("button", { name: "Private" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Owner only" }),
    ).toBeInTheDocument();
  });

  it("item thumbnails are 18px radius", () => {
    render(
      <GalleryDrawer galleryId="g1" onClose={() => {}} onOpenItem={() => {}} />,
    );
    const li = screen.getByRole("button", { name: "Sunset" }).closest("li")!;
    expect(li.className).toContain("rounded-[18px]");
  });
});

describe("MediaThumb object position", () => {
  it("accepts an object position so covers can crop to the top third", () => {
    const { container } = render(
      <MediaThumb mediaId="m1" objectPosition="50% 30%" />,
    );
    const img = container.querySelector("img")!;
    expect(img.style.objectPosition).toBe("50% 30%");
  });
});

describe("Drawer brand", () => {
  it("right sheet floats as a rounded glass panel", () => {
    render(
      <Drawer open onClose={() => {}} title="Camping" side="right">
        x
      </Drawer>,
    );
    const dlg = screen.getByRole("dialog", { name: "Camping" });
    expect(dlg.className).toContain("glass");
    expect(dlg.className).toContain("rounded-[32px]");
    expect(dlg.className).not.toContain("border-l");
    expect(
      screen.getByRole("heading", { name: "Camping", level: 2 }).className,
    ).toContain("text-xl");
  });
});
