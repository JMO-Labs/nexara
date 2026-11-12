/**
 * @file tests/unit/galleries/GalleryDrawer.test.tsx
 * @brief Drawer must not stay mounted as a modal layer while the Lightbox is open
 *        (Radix modal would block the Lightbox's pointer events and focus).
 */
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { GalleryDrawer } from "@/components/galleries/galleries-page/GalleryDrawer";

const detail = vi.hoisted(() => ({
  current: { id: "g1", title: "Camping" } as Record<string, unknown>,
}));

vi.mock("@/hooks/useGalleries", () => {
  const mut = () => ({ mutate: vi.fn(), isPending: false });
  return {
    useGalleryDetail: () => ({ data: detail.current }),
    useGalleryItems: () => ({ data: [], isLoading: false }),
    useUpdateGallery: mut,
    useDeleteGallery: mut,
    useRemoveItem: mut,
  };
});
vi.mock("@/hooks/useEvents", () => ({
  useEventDetail: () => ({ data: undefined }),
}));
vi.mock("@/components/galleries/GalleryUpload", () => ({
  GalleryUpload: () => null,
}));
vi.mock("@/components/galleries/galleries-page/GalleryCollaborators", () => ({
  GalleryCollaborators: () => <div data-testid="collabs" />,
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

test("contributors section shows only for the collaborators policy", () => {
  detail.current = {
    id: "g1",
    title: "Camping",
    contribution_policy: "owner_only",
  };
  const { unmount } = render(<GalleryDrawer {...props} />);
  expect(screen.queryByTestId("collabs")).toBeNull();
  unmount();
  detail.current = {
    id: "g1",
    title: "Camping",
    contribution_policy: "collaborators",
  };
  render(<GalleryDrawer {...props} />);
  expect(screen.getByTestId("collabs")).toBeInTheDocument();
});

test("drawer shows Event gallery badge only when event_id is set", () => {
  detail.current = { id: "g1", title: "Camping", event_id: "e1" };
  const { unmount } = render(<GalleryDrawer {...props} />);
  expect(screen.getByText("Event gallery")).toBeInTheDocument();
  unmount();
  detail.current = { id: "g1", title: "Camping", event_id: null };
  render(<GalleryDrawer {...props} />);
  expect(screen.queryByText("Event gallery")).toBeNull();
});
