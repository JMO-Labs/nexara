/**
 * @file tests/unit/home/HomeSideColumn.test.tsx
 * @brief Side column: auto mode by default, collapse/expand persisted.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/hooks/useHomePeople", () => ({
  useHomePeople: () => ({ data: { items: [{ birthday_in_days: 2 }] } }),
}));
vi.mock("@/components/home/tiles/PeopleTile", () => ({
  PeopleTile: () => <section>people</section>,
}));
vi.mock("@/components/home/tiles/ListsTile", () => ({
  ListsTile: () => <section>lists</section>,
}));

import { HomeSideColumn } from "@/components/home/HomeSideColumn";

const rail = () => screen.getByRole("navigation", { name: "Side column" });

describe("HomeSideColumn", () => {
  beforeEach(() => localStorage.clear());

  it("defaults to auto: rail below 3xl, open at 3xl", () => {
    renderWithProviders(<HomeSideColumn open={null} onToggle={vi.fn()} />);
    expect(rail().className).toContain("3xl:hidden");
    expect(
      screen.getByLabelText("People, 1 birthday soon"),
    ).toBeInTheDocument();
  });

  it("collapses and expands, remembering the choice", () => {
    renderWithProviders(<HomeSideColumn open={null} onToggle={vi.fn()} />);
    fireEvent.click(screen.getByLabelText("Collapse side column"));
    expect(localStorage.getItem("nx-home-side")).toBe("closed");
    expect(rail().className).toContain("lg:flex");
    expect(rail().className).not.toContain("3xl:hidden");
    fireEvent.click(screen.getByLabelText("Expand side column"));
    expect(localStorage.getItem("nx-home-side")).toBe("open");
    expect(rail().className).toContain("lg:hidden");
  });
});
