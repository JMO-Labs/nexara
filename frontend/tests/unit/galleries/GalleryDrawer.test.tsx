/**
 * @file tests/unit/galleries/GalleryDrawer.test.tsx
 * @brief Drawer must not stay mounted as a modal layer while the Lightbox is open
 *        (Radix modal would block the Lightbox's pointer events and focus).
 */
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { GalleryDrawer } from "@/components/galleries/galleries-page/GalleryDrawer";

const detail = vi.hoisted(() => ({ event_id: null as string | null }));
vi.mock("@/hooks/useGalleries", () => {
  const mut = () => ({ mutate: vi.fn(), isPending: false });
  return {
    useGalleryDetail: () => ({
      data: { id: "g1", title: "Camping", event_id: detail.event_id },
    }),
    useGalleryItems: () => ({ data: [], isLoading: false }),
    useUpdateGallery: mut,
    useDeleteGallery: mut,
    useRemoveItem: mut,
  };
});
vi.mock("@/components/galleries/GalleryUpload", () => ({
  GalleryUpload: () => null,
}));

const props = { galleryId: "g1", onClose: vi.fn(), onOpenItem: vi.fn() };

test("drawer is open when a gallery is selected", () => {
  render(<GalleryDrawer {...props} />);
  expect(screen.getByRole("dialog", { name: "Camping" })).toBeInTheDocument();
});

test("drawer closes while the lightbox is suspended over it", () => {
  render(<GalleryDrawer {...props} suspended />);
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("drawer shows Event gallery badge only when event_id is set", () => {
  detail.event_id = "e1";
  const { unmount } = render(<GalleryDrawer {...props} />);
  expect(screen.getByText("Event gallery")).toBeInTheDocument();
  unmount();
  detail.event_id = null;
  render(<GalleryDrawer {...props} />);
  expect(screen.queryByText("Event gallery")).toBeNull();
});
