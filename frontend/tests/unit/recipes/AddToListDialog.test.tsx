/**
 * @file tests/unit/recipes/AddToListDialog.test.tsx
 * @brief Dialog posts selected ingredient indexes and toasts the result.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const m = vi.hoisted(() => ({
  add: vi.fn(),
  push: vi.fn(),
  router: vi.fn(),
}));
vi.mock("@/lib/api/recipes", () => ({ addToShoppingList: m.add }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: m.router }) }));
vi.mock("@/hooks/useLists", () => ({
  useLists: () => ({
    data: {
      lists: [
        { id: "l1", title: "Mine", ownerId: "u1", status: "active" },
        { id: "l2", title: "Theirs", ownerId: "u2", status: "active" },
      ],
    },
  }),
}));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { id: "u1", community_id: "c1" } }),
}));
vi.mock("@/stores/toasts", () => ({
  useToasts: (sel: (s: unknown) => unknown) => sel({ push: m.push }),
}));

import { AddToListDialog } from "@/components/recipes/AddToListDialog";
import type { Recipe } from "@/lib/api/recipes";

const recipe = {
  id: "r1",
  ingredients: [
    { qty: "1 cup", item: "cornmeal" },
    { qty: "", item: "salt" },
  ],
} as Recipe;

describe("AddToListDialog", () => {
  it("adds only checked ingredients to a new list", async () => {
    m.add.mockResolvedValue({ list_id: "n1", added: 1 });
    const u = userEvent.setup();
    render(<AddToListDialog recipe={recipe} />);
    await u.click(
      screen.getByRole("button", { name: /add to shopping list/i }),
    );
    await u.click(screen.getByLabelText("salt"));
    await u.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() =>
      expect(m.add).toHaveBeenCalledWith("r1", {
        list_id: null,
        ingredients: [0],
      }),
    );
    expect(m.push.mock.calls[0][0].message).toBe("Added 1 items");
  });

  it("disables Add when nothing is selected", async () => {
    const u = userEvent.setup();
    render(<AddToListDialog recipe={recipe} />);
    await u.click(
      screen.getByRole("button", { name: /add to shopping list/i }),
    );
    await u.click(screen.getByLabelText("1 cup cornmeal"));
    await u.click(screen.getByLabelText("salt"));
    expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
  });
});
