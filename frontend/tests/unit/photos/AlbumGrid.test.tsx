/**
 * @file tests/unit/photos/AlbumGrid.test.tsx
 * @brief AlbumGrid: expand-on-hover/focus cards, states, phone accordion.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AlbumGrid } from "@/components/photos/AlbumGrid";
import type { Gallery } from "@/lib/api/galleries";

const mobile = vi.hoisted(() => ({ value: false }));
vi.mock("@/hooks/useIsMobile", () => ({ useIsMobile: () => mobile.value }));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: () => <span data-testid="thumb" />,
}));

const g = (id: string, n = 3): Gallery => ({
  id,
  owner_id: "u1",
  title: `Album ${id}`,
  description: null,
  cover_media_id: `m${id}`,
  event_id: null,
  subgroup_id: null,
  visibility: "community",
  contribution_policy: "owner_only",
  item_count: n,
  is_featured: false,
  is_default: false,
  is_event_gallery: false,
  created_at: "",
  updated_at: "",
});

beforeEach(() => {
  mobile.value = false;
});

describe("AlbumGrid", () => {
  it("hides details until a card is hovered", async () => {
    render(<AlbumGrid items={[g("1"), g("2")]} onSelect={() => {}} />);
    expect(screen.queryByText("Open album")).toBeNull();
    await userEvent.hover(screen.getByRole("button", { name: /Album 1/ }));
    expect(screen.getByText("Open album")).toBeInTheDocument();
    expect(
      within(screen.getByRole("button", { name: /Album 1/ })).getByText(
        "3 photos",
      ),
    ).toBeInTheDocument();
    await userEvent.unhover(screen.getByRole("button", { name: /Album 1/ }));
    expect(screen.queryByText("Open album")).toBeNull();
  });

  it("expands on keyboard focus and opens on Enter", async () => {
    const onSelect = vi.fn();
    render(<AlbumGrid items={[g("1"), g("2")]} onSelect={onSelect} />);
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /Album 1/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Open album")).toBeInTheDocument();
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("1");
  });

  it("singular photo count", async () => {
    render(<AlbumGrid items={[g("1", 1)]} onSelect={() => {}} />);
    await userEvent.hover(screen.getByRole("button"));
    expect(screen.getByText("1 photo")).toBeInTheDocument();
  });

  it("phone: first tap expands, second tap opens", async () => {
    mobile.value = true;
    const onSelect = vi.fn();
    render(<AlbumGrid items={[g("1"), g("2")]} onSelect={onSelect} />);
    const btn = screen.getByRole("button", { name: /Album 2/ });
    await userEvent.click(btn);
    expect(onSelect).not.toHaveBeenCalled();
    expect(btn).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(btn);
    expect(onSelect).toHaveBeenCalledWith("2");
  });

  it("empty state with custom action", () => {
    render(
      <AlbumGrid
        items={[]}
        onSelect={() => {}}
        empty={<span>make one</span>}
      />,
    );
    expect(screen.getByText("No albums yet")).toBeInTheDocument();
    expect(screen.getByText("make one")).toBeInTheDocument();
  });

  it("loading is a busy region", () => {
    render(<AlbumGrid items={undefined} isLoading onSelect={() => {}} />);
    expect(screen.getByTestId("album-skeleton")).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });

  it("error offers retry", async () => {
    const onRetry = vi.fn();
    render(
      <AlbumGrid
        items={undefined}
        error={new Error("boom")}
        onRetry={onRetry}
        onSelect={() => {}}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("caption uses a guaranteed-contrast scrim token, not glass", () => {
    render(<AlbumGrid items={[g("1")]} onSelect={() => {}} />);
    const cap = screen.getByText("Album 1").parentElement!;
    expect(cap).toHaveClass("bg-[var(--nx-scrim)]");
    expect(cap).toHaveClass("text-[var(--nx-on-scrim)]");
    expect(cap).not.toHaveClass("glass-item");
  });

  it("phone closed cards are taller (h-36)", () => {
    mobile.value = true;
    render(<AlbumGrid items={[g("1")]} onSelect={() => {}} />);
    expect(screen.getByRole("button", { name: "Album 1" })).toHaveClass("h-36");
  });

  it("no-cover glyph sits top-left so it never overlaps the caption", () => {
    render(
      <AlbumGrid
        items={[{ ...g("1"), cover_media_id: null }]}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByTestId("album-placeholder")).toHaveClass(
      "items-start",
      "justify-start",
    );
  });
});
