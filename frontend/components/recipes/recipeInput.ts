/**
 * @file components/recipes/recipeInput.ts
 * @brief Map recipe form state to the API body.
 */
import type {
  Ingredient,
  RecipeInput,
  RecipeVisibility,
} from "@/lib/api/recipes";

const num = (v: string) => (v.trim() === "" ? null : Number(v));

/**
 * @brief Build the API body from form state (drops blank rows, dedupes tags).
 * @param s raw form state
 * @return RecipeInput
 */
export function toInput(s: {
  title: string;
  story: string;
  ingredients: Ingredient[];
  steps: string[];
  servings: string;
  prep: string;
  cook: string;
  photos: string[];
  maker: string;
  tags: string;
  visibility: RecipeVisibility;
  subgroup: string;
}): RecipeInput {
  const [kind, id] = s.maker.split(":");
  return {
    title: s.title.trim(),
    story: s.story,
    ingredients: s.ingredients
      .map((i) => ({ qty: i.qty.trim(), item: i.item.trim() }))
      .filter((i) => i.item),
    steps: s.steps.map((x) => x.trim()).filter(Boolean),
    servings: num(s.servings),
    prep_minutes: num(s.prep),
    cook_minutes: num(s.cook),
    photo_media_ids: s.photos,
    best_maker_user_id: kind === "user" ? id : null,
    best_maker_household_id: kind === "household" ? id : null,
    tags: [
      ...new Set(
        s.tags
          .split(",")
          .map((t) => t.trim().toLowerCase())
          .filter(Boolean),
      ),
    ],
    visibility: s.visibility,
    subgroup_id: s.visibility === "subgroup" ? s.subgroup || null : null,
  };
}
