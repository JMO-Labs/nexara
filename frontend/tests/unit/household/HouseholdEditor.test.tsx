/**
 * @file tests/unit/household/HouseholdEditor.test.tsx
 * @brief HouseholdEditor: pet-only fields, payload shape, name required.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const create = vi.fn();
vi.mock("@/hooks/useHousehold", () => ({
  useSaveHousehold: () => ({
    create: { mutate: create, isPending: false },
    update: { mutate: vi.fn(), isPending: false },
    remove: { mutate: vi.fn(), isPending: false },
  }),
}));
vi.mock("@/components/media/CoverPicker", () => ({ CoverPicker: () => null }));

import { HouseholdEditor } from "@/components/household/HouseholdEditor";

describe("HouseholdEditor", () => {
  beforeEach(() => {
    create.mockReset();
  });

  it("person form hides pet fields", () => {
    renderWithProviders(
      <HouseholdEditor member={null} kind="person" onClose={() => {}} />,
    );
    expect(screen.getByText("Add a family member")).toBeInTheDocument();
    expect(screen.queryByText("Species")).toBeNull();
    expect(screen.queryByText("Care card")).toBeNull();
  });

  it("pet form sends trimmed lists and private care card by default", async () => {
    renderWithProviders(
      <HouseholdEditor member={null} kind="pet" onClose={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: " Biscuit " },
    });
    fireEvent.change(screen.getByLabelText("Likes"), {
      target: { value: "walks, , naps" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    const body = create.mock.calls[0][0];
    expect(body).toMatchObject({
      kind: "pet",
      name: "Biscuit",
      likes: ["walks", "naps"],
      care_visibility: "private",
      visibility: "groups",
    });
  });
});
