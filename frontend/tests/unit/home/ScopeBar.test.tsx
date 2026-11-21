/**
 * @file tests/unit/home/ScopeBar.test.tsx
 * @brief ScopeBar: member-group pills set the scope store.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({
    data: [
      { id: "g1", name: "Book club", accent_color: "#112233", is_member: true },
      { id: "g2", name: "Chess", accent_color: null, is_member: false },
    ],
  }),
}));

import { ScopeBar } from "@/components/home/ScopeBar";
import { useHomeScope } from "@/stores/homeScope";

beforeEach(() => useHomeScope.getState().setScope("all"));

describe("ScopeBar", () => {
  it("lists Everything and only member groups", () => {
    renderWithProviders(<ScopeBar needs={<span>needs-slot</span>} />);
    expect(screen.getByRole("button", { name: /Everything/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /Book club/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Chess/ })).toBeNull();
    expect(screen.getByText("needs-slot")).toBeInTheDocument();
  });

  it("selects a group on click", () => {
    renderWithProviders(<ScopeBar needs={null} />);
    fireEvent.click(screen.getByRole("button", { name: /Book club/ }));
    expect(useHomeScope.getState().scope).toBe("g1");
    expect(screen.getByRole("button", { name: /Book club/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
