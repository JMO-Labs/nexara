/**
 * @file tests/unit/galleries/GallerySortSelect.test.tsx
 * @brief Sort pill row changes sort order and fires callback.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GallerySortSelect } from "@/components/galleries/GallerySortSelect";

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("GallerySortSelect", () => {
  it("renders three sort options", () => {
    wrap(<GallerySortSelect sort="recent" onSortChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Recent" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Popular" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Oldest" })).toBeInTheDocument();
  });

  it("highlights active sort option", () => {
    wrap(<GallerySortSelect sort="recent" onSortChange={() => {}} />);
    const recentBtn = screen.getByRole("button", { name: "Recent" });
    expect(recentBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSortChange with selected sort", async () => {
    const mockOnChange = vi.fn();
    wrap(<GallerySortSelect sort="recent" onSortChange={mockOnChange} />);

    const popularBtn = screen.getByRole("button", { name: "Popular" });
    await userEvent.click(popularBtn);

    expect(mockOnChange).toHaveBeenCalledWith("popular");
  });

  it("changes active state when sort prop changes", () => {
    const { rerender } = render(
      <>
        <GallerySortSelect sort="recent" onSortChange={() => {}} />
      </>,
    );

    let recentBtn = screen.getByRole("button", { name: "Recent" });
    expect(recentBtn).toHaveAttribute("aria-pressed", "true");

    rerender(
      <>
        <GallerySortSelect sort="popular" onSortChange={() => {}} />
      </>,
    );

    const popularBtn = screen.getByRole("button", { name: "Popular" });
    expect(popularBtn).toHaveAttribute("aria-pressed", "true");

    recentBtn = screen.getByRole("button", { name: "Recent" });
    expect(recentBtn).toHaveAttribute("aria-pressed", "false");
  });
});
