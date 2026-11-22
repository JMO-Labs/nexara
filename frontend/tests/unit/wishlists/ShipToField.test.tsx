/**
 * @file tests/unit/wishlists/ShipToField.test.tsx
 * @brief Ship-to picker: people without a shared address are listed but disabled.
 */
import { describe, it, expect, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { ShipToField } from "@/components/wishlists/wizard/ShipToField";
import { initialDraft } from "@/components/wishlists/wizard/draft";

vi.mock("@/lib/api/wishlists", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/wishlists")>()),
  listShipPeople: vi.fn().mockResolvedValue([
    { id: "u2", display_name: "Marcus", available: false },
    { id: "u3", display_name: "Grandma", available: true },
  ]),
}));
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: () => ({ data: { items: [] } }),
}));

describe("ShipToField", () => {
  it("lists sharers first and disables the rest", async () => {
    const d = { ...initialDraft(null), ship_mode: "user" as const };
    renderWithProviders(<ShipToField d={d} set={() => {}} />);
    const select = screen.getByLabelText(/Person/);
    const grandma = await within(select).findByRole("option", {
      name: "Grandma",
    });
    const marcus = within(select).getByRole("option", {
      name: "Marcus (doesn't share their address)",
    });
    expect(grandma).not.toBeDisabled();
    expect(marcus).toBeDisabled();
    const names = within(select)
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(names.indexOf("Grandma")).toBeLessThan(
      names.indexOf(marcus.textContent),
    );
  });
});
