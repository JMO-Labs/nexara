/**
 * @file tests/unit/photos/brand-albums.test.tsx
 * @brief Brand rules for albums and all-photos: glass caption pills, ink
 *        "Open album" pill, soft placeholder for empty albums, 22px tiles,
 *        friendly date groups.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { format } from "date-fns";
import { AlbumGrid } from "@/components/photos/AlbumGrid";
import { AllPhotos } from "@/components/photos/AllPhotos";
import type { Gallery } from "@/lib/api/galleries";
import type { HomeMediaItem } from "@/lib/api/home";

const mobile = vi.hoisted(() => ({ value: false }));
vi.mock("@/hooks/useIsMobile", () => ({ useIsMobile: () => mobile.value }));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: () => <span data-testid="thumb" />,
}));

const g = (id: string, cover: string | null = `m${id}`): Gallery =>
  ({
    id,
    owner_id: "u1",
    title: `Album ${id}`,
    description: null,
    cover_media_id: cover,
    event_id: null,
    subgroup_id: null,
    visibility: "community",
    contribution_policy: "owner_only",
    item_count: 5,
    is_featured: false,
    is_default: false,
    is_event_gallery: false,
    created_at: "",
    updated_at: "",
  }) as Gallery;

describe("AlbumGrid brand", () => {
  it("has no heavy black gradient scrim", () => {
    const { container } = render(
      <AlbumGrid items={[g("1")]} onSelect={() => {}} />,
    );
    expect(container.innerHTML).not.toContain("from-black");
    expect(container.innerHTML).not.toContain("bg-gradient");
  });

  it("caption is a glass pill with ink text and a visible count", () => {
    render(<AlbumGrid items={[g("1")]} onSelect={() => {}} />);
    const count = screen.getByText("5 photos");
    expect(count.closest(".glass-item")).not.toBeNull();
  });

  it("Open album pill is the ink pill, not white", async () => {
    render(<AlbumGrid items={[g("1")]} onSelect={() => {}} />);
    await userEvent.hover(screen.getByRole("button", { name: /Album 1/ }));
    const pill = screen.getByText("Open album");
    expect(pill.className).toContain("bg-surface-strong");
    expect(pill.className).not.toContain("bg-white");
    expect(pill.className).not.toContain("text-black");
  });

  it("closed phone cards are 144px tall (h-36), not h-28", () => {
    render(<AlbumGrid items={[g("1")]} onSelect={() => {}} />);
    const card = screen.getByRole("button", { name: /Album 1/ });
    expect(card.className).toContain("h-36");
    expect(card.className).not.toContain("h-28");
  });

  it("albums without a cover get a soft placeholder tile", () => {
    render(<AlbumGrid items={[g("9", null)]} onSelect={() => {}} />);
    expect(screen.getByTestId("album-placeholder")).toBeInTheDocument();
  });

  it("albums with a cover do not render the placeholder", () => {
    render(<AlbumGrid items={[g("1")]} onSelect={() => {}} />);
    expect(screen.queryByTestId("album-placeholder")).toBeNull();
  });
});

const item = (id: string, createdAt: string): HomeMediaItem =>
  ({
    source: "post",
    source_id: "s1",
    source_title: null,
    media_id: id,
    media: { id, filename: `${id}.jpg`, alt_text: "", created_at: createdAt },
  }) as unknown as HomeMediaItem;

describe("AllPhotos brand", () => {
  it("tiles use the 22px item radius", () => {
    render(
      <AllPhotos
        items={[item("a", new Date().toISOString())]}
        isLoading={false}
        error={null}
        onOpen={() => {}}
      />,
    );
    const tile = screen.getByRole("button", { name: /Open photo/ });
    expect(tile.className).toContain("rounded-[22px]");
  });

  it("groups recent photos under a friendly 'This week' label", () => {
    render(
      <AllPhotos
        items={[item("a", new Date().toISOString())]}
        isLoading={false}
        error={null}
        onOpen={() => {}}
      />,
    );
    expect(screen.getByText("This week")).toBeInTheDocument();
  });

  it("older photos are grouped by month and year", () => {
    const old = new Date(2020, 2, 4).toISOString();
    render(
      <AllPhotos
        items={[item("b", old)]}
        isLoading={false}
        error={null}
        onOpen={() => {}}
      />,
    );
    expect(
      screen.getByText(format(new Date(2020, 2, 4), "MMMM yyyy")),
    ).toBeInTheDocument();
  });

  it("skeleton tiles use the 22px radius", () => {
    render(
      <AllPhotos items={undefined} isLoading error={null} onOpen={() => {}} />,
    );
    const skel = screen.getByTestId("photos-skeleton").firstElementChild!;
    expect(skel.className).toContain("rounded-[22px]");
  });
});
