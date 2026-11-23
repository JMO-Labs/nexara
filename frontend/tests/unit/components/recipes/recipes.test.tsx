/**
 * @file tests/unit/components/recipes/recipes.test.tsx
 * @brief Recipe card/view render, ingredient checkboxes and form body mapping.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecipeCard } from "@/components/recipes/RecipeCard";
import { RecipeView } from "@/components/recipes/RecipeView";
import { toInput } from "@/components/recipes/recipeInput";
import type { Recipe } from "@/lib/api/recipes";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/hooks/useLists", () => ({ useLists: () => ({ data: undefined }) }));

const recipe: Recipe = {
  id: "r1",
  title: "Cornbread",
  story: "Gran's Sunday bread.",
  ingredients: [
    { qty: "2 cups", item: "cornmeal" },
    { qty: "", item: "salt" },
  ],
  steps: ["Mix", "Bake"],
  servings: 8,
  prep_minutes: 10,
  cook_minutes: 25,
  photo_media_ids: [],
  best_maker_user_id: "u1",
  best_maker_household_id: null,
  best_maker_name: "Ruth",
  tags: ["dinner"],
  visibility: "community",
  subgroup_id: null,
  author: { id: "u2", display_name: "Maya" },
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

describe("recipes", () => {
  it("card links to the recipe and shows the best maker", () => {
    render(<RecipeCard recipe={recipe} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/app/recipes/r1");
    expect(screen.getByText("Made best by Ruth")).toBeInTheDocument();
  });

  it("view shows story, ingredients, numbered steps and the maker chip", async () => {
    render(<RecipeView recipe={recipe} />);
    expect(screen.getByText("Gran's Sunday bread.")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").length).toBeGreaterThan(4);
    const box = screen.getByRole("checkbox", { name: /2 cups cornmeal/ });
    await userEvent.click(box);
    expect(box).toBeChecked();
    expect(screen.getByText("Made best by Ruth")).toBeInTheDocument();
  });

  it("toInput drops blank rows, dedupes tags and splits the maker", () => {
    const out = toInput({
      title: " Pie ",
      story: "",
      ingredients: [
        { qty: "1", item: "apple" },
        { qty: "", item: " " },
      ],
      steps: ["bake", " "],
      servings: "4",
      prep: "",
      cook: "30",
      photos: ["m1"],
      maker: "household:h1",
      tags: "Dessert, dessert, ",
      visibility: "private",
      subgroup: "g1",
    });
    expect(out).toMatchObject({
      title: "Pie",
      ingredients: [{ qty: "1", item: "apple" }],
      steps: ["bake"],
      servings: 4,
      prep_minutes: null,
      cook_minutes: 30,
      best_maker_user_id: null,
      best_maker_household_id: "h1",
      tags: ["dessert"],
      subgroup_id: null,
    });
  });
});
