/**
 * @file tests/unit/subgroups/hub/GalleriesTab.test.tsx
 * @brief Hub GalleriesTab renders AlbumGrid and links into /app/photos.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { GalleriesTab } from "@/components/subgroups/hub/GalleriesTab";
import type { SubgroupDetail } from "@/lib/api/subgroups";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
const list = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/useGalleries", () => ({
  useGalleryList: (p: unknown) => list(p),
}));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: () => null,
}));
vi.mock("@/components/galleries/GalleryCreateModal", () => ({
  GalleryCreateModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="create" /> : null,
}));
vi.mock("@/components/galleries/GalleryUploadModal", () => ({
  GalleryUploadModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="upload" /> : null,
}));

const sg = (role: string | null) =>
  ({ id: "s1", slug: "s", my_role: role }) as unknown as SubgroupDetail;
const album = { id: "g1", title: "Camp", item_count: 2, cover_media_id: null };

beforeEach(() => {
  push.mockClear();
  list.mockReturnValue({ data: { items: [album] }, isLoading: false });
});

describe("hub GalleriesTab", () => {
  it("filters by subgroup and opens an album in /app/photos", async () => {
    render(<GalleriesTab subgroup={sg("member")} />);
    expect(list).toHaveBeenCalledWith({ subgroup_id: "s1" });
    await userEvent.click(screen.getByRole("button", { name: "Camp" }));
    expect(push).toHaveBeenCalledWith("/app/photos?gallery=g1");
  });

  it("members can create albums and upload", async () => {
    render(<GalleriesTab subgroup={sg("member")} />);
    await userEvent.click(screen.getByRole("button", { name: "New album" }));
    expect(screen.getByTestId("create")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Upload media" }));
    expect(screen.getByTestId("upload")).toBeInTheDocument();
  });

  it("non-members get no actions", () => {
    render(<GalleriesTab subgroup={sg(null)} />);
    expect(screen.queryByRole("button", { name: "New album" })).toBeNull();
  });
});
