/**
 * @file tests/unit/components/galleries/Slideshow.test.tsx
 * @brief Slideshow: keyboard nav, pause toggle, reduced-motion safe classes.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Slideshow } from "@/components/galleries/Slideshow";
import type { GalleryItem } from "@/lib/api/galleries";

vi.mock("@/hooks/useMembers", () => ({
  useMemberProfile: () => ({ data: { display_name: "Ruth" } }),
}));

const mk = (i: number): GalleryItem => ({
  id: `i${i}`,
  gallery_id: "g",
  media_id: `m${i}`,
  added_by: "u",
  caption: `Cap ${i}`,
  position: i,
  created_at: "",
});

describe("Slideshow", () => {
  it("ArrowRight advances and shows caption plus uploader", async () => {
    render(<Slideshow items={[mk(0), mk(1)]} />);
    expect(screen.getByAltText("Cap 0")).toBeInTheDocument();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByAltText("Cap 1")).toBeInTheDocument();
    expect(screen.getByText(/Cap 1 · Added by Ruth/)).toBeInTheDocument();
  });

  it("Space toggles pause via aria-pressed", async () => {
    render(<Slideshow items={[mk(0), mk(1)]} />);
    const btn = screen.getByRole("button", { name: /pause slideshow/i });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.keyboard(" ");
    expect(
      screen.getByRole("button", { name: /play slideshow/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("only animates under motion-safe", () => {
    render(<Slideshow items={[mk(0)]} />);
    const cls = screen.getByAltText("Cap 0").className;
    expect(cls).toContain("motion-safe:transition-opacity");
    expect(cls.split(" ")).not.toContain("transition-opacity");
  });

  it("Escape calls onExit", async () => {
    const onExit = vi.fn();
    render(<Slideshow items={[mk(0)]} onExit={onExit} />);
    await userEvent.keyboard("{Escape}");
    expect(onExit).toHaveBeenCalled();
  });
});
