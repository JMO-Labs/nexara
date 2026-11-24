/**
 * @file tests/unit/ui/page/TwoPane.test.tsx
 * @brief TwoPane layout.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TwoPane } from "@/components/ui/page";

describe("TwoPane", () => {
  it("renders aside and main with aside width var", () => {
    render(
      <TwoPane aside={<div>side</div>} asideWidth={280}>
        <div>main</div>
      </TwoPane>,
    );
    expect(screen.getByText("side")).toBeInTheDocument();
    expect(screen.getByText("main")).toBeInTheDocument();
    const grid = screen
      .getByText("side")
      .closest("[data-slot='two-pane']") as HTMLElement;
    expect(grid.style.getPropertyValue("--aside-w")).toBe("280px");
  });
  it("defaults aside width to 300", () => {
    render(<TwoPane aside="s">m</TwoPane>);
    const grid = screen
      .getByText("s")
      .closest("[data-slot='two-pane']") as HTMLElement;
    expect(grid.style.getPropertyValue("--aside-w")).toBe("300px");
  });
  it("offsets the sticky aside below the top bar", () => {
    render(<TwoPane aside={<nav>side</nav>}>main</TwoPane>);
    expect(screen.getByText("side").closest("aside")?.className).toContain(
      "md:top-20",
    );
  });
});
