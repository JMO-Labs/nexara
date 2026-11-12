/**
 * @file tests/unit/components/galleries/GalleryGrid.test.tsx
 * @brief GalleryGrid states: loading, error retry, empty CTA, responsive grid.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GalleryGrid } from "@/components/galleries/GalleryGrid";

const state: Record<string, unknown> = {};
const refetch = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/hooks/useGalleries", () => ({
  useGalleryList: () => ({ refetch, ...state }),
}));

const g = (id: string) => ({
  id,
  title: `Gal ${id}`,
  owner_id: "u1",
  item_count: 2,
  cover_media_id: null,
  is_featured: false,
});

describe("GalleryGrid", () => {
  beforeEach(() => {
    for (const k of Object.keys(state)) delete state[k];
    refetch.mockClear();
  });

  it("shows skeleton busy region while loading", () => {
    state.isLoading = true;
    const { container } = render(<GalleryGrid onSelect={vi.fn()} />);
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it("retry refetches the query", async () => {
    state.error = new Error("boom");
    render(<GalleryGrid onSelect={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it("empty state offers Create gallery CTA", async () => {
    const onCreate = vi.fn();
    state.data = { items: [] };
    render(<GalleryGrid onSelect={vi.fn()} onCreate={onCreate} />);
    await userEvent.click(
      screen.getByRole("button", { name: /create gallery/i }),
    );
    expect(onCreate).toHaveBeenCalled();
  });

  it("empty state says Browse media without onCreate", () => {
    state.data = { items: [] };
    render(<GalleryGrid onSelect={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /browse media/i }),
    ).toBeInTheDocument();
  });

  it("grid is 2-col mobile, 3 md, 4 lg", () => {
    state.data = { items: [g("1"), g("2")] };
    const { container } = render(<GalleryGrid onSelect={vi.fn()} />);
    const grid = container.firstElementChild!;
    expect(grid.className).toMatch(
      /grid-cols-2.*md:grid-cols-3.*lg:grid-cols-4/,
    );
  });
});
