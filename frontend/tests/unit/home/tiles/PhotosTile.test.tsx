/**
 * @file tests/unit/home/tiles/PhotosTile.test.tsx
 * @brief PhotosTile: mosaic, cap, empty state.
 */
import { describe, it, expect, vi } from "vitest";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/app",
}));
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../../utils/renderWithProviders";

let data: unknown = { items: [], next_cursor: null };
vi.mock("@/hooks/useHomeMedia", () => ({
  useHomeMedia: () => ({ data }),
}));

import { PhotosTile } from "@/components/home/tiles/PhotosTile";

const item = (i: number) => ({
  media_id: `m${i}`,
  media: { id: `m${i}`, thumbnail_key: "t", alt_text: i === 0 ? "Cake" : null },
  source_title: i === 0 ? "Birthday" : null,
});

const ui = () => <PhotosTile open onToggle={() => {}} />;

describe("PhotosTile", () => {
  it("renders at most 7 object-cover imgs and titles from first source", () => {
    data = {
      items: Array.from({ length: 9 }, (_, i) => item(i)),
      next_cursor: "x",
    };
    const { container } = renderWithProviders(ui());
    const imgs = container.querySelectorAll("img");
    expect(imgs).toHaveLength(7);
    imgs.forEach((i) => expect(i.className).toContain("object-cover"));
    expect(imgs[0]).toHaveAttribute("alt", "Cake");
    expect(imgs[0]).toHaveAttribute("src", "/api/v1/media/m0/thumbnail");
    expect(
      screen.getByRole("heading", { name: "Birthday" }),
    ).toBeInTheDocument();
    expect(screen.getByText("+")).toBeInTheDocument();
    expect(container.querySelector(".sweep")).toBeNull();
  });

  it("shows an empty state", () => {
    data = { items: [], next_cursor: null };
    renderWithProviders(ui());
    expect(screen.getByText("No photos yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Upload photos" })).toHaveAttribute(
      "href",
      "/app/galleries",
    );
  });
});
