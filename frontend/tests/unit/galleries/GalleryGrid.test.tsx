/**
 * @file tests/unit/galleries/GalleryGrid.test.tsx
 * @brief GalleryGrid renders cards, empty state, and error state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { GalleryGrid } from "@/components/galleries/GalleryGrid";
import * as api from "@/lib/api/galleries";
import type { Gallery, GalleryListResponse } from "@/lib/api/galleries";

vi.mock("@/lib/api/galleries");
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
}));

const mk = (id: string, title: string): Gallery => ({
  id,
  owner_id: "u1",
  title,
  description: null,
  cover_media_id: null,
  event_id: null,
  subgroup_id: null,
  visibility: "community",
  contribution_policy: "owner_only",
  item_count: 2,
  is_featured: false,
  is_default: false,
  is_event_gallery: false,
  created_at: "2026-04-25T00:00:00Z",
  updated_at: "2026-04-25T00:00:00Z",
});

const page = (items: Gallery[]): GalleryListResponse => ({
  items,
  next_cursor: null,
  has_more: false,
});

describe("GalleryGrid", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders a card per gallery and forwards selection", async () => {
    vi.mocked(api.listGalleries).mockResolvedValue(
      page([mk("g1", "Trip"), mk("g2", "Party")]),
    );
    const onSelect = vi.fn();
    renderWithProviders(<GalleryGrid onSelect={onSelect} />);
    expect(await screen.findByText("Trip")).toBeInTheDocument();
    expect(screen.getByText("Party")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Trip"));
    expect(onSelect).toHaveBeenCalledWith("g1");
  });

  it("renders the empty state and navigates to media", async () => {
    vi.mocked(api.listGalleries).mockResolvedValue(page([]));
    renderWithProviders(<GalleryGrid onSelect={() => {}} />);
    expect(await screen.findByText("No galleries yet")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Browse media" }));
    expect(push).toHaveBeenCalledWith("/app/media");
  });

  it("uses onCreate for the empty-state action when provided", async () => {
    vi.mocked(api.listGalleries).mockResolvedValue(page([]));
    const onCreate = vi.fn();
    renderWithProviders(
      <GalleryGrid onSelect={() => {}} onCreate={onCreate} />,
    );
    await screen.findByText("No galleries yet");
    fireEvent.click(screen.getByRole("button", { name: "Create gallery" }));
    expect(onCreate).toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it("renders an error state when loading fails", async () => {
    vi.mocked(api.listGalleries).mockRejectedValue(new Error("boom"));
    renderWithProviders(<GalleryGrid onSelect={() => {}} />);
    await waitFor(() =>
      expect(screen.getByText("Couldn't load galleries")).toBeInTheDocument(),
    );
  });
});
