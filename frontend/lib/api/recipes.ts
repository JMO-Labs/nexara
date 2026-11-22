/**
 * @file lib/api/recipes.ts
 * @brief Recipe book REST client (wire format is snake_case).
 */
import { apiDelete, apiGet, apiPost, apiPut, seg } from "./client";

export interface Ingredient {
  qty: string;
  item: string;
}

export type RecipeVisibility = "community" | "subgroup" | "private";

/** @brief Editable recipe fields (create body and update body). */
export interface RecipeInput {
  title: string;
  story: string;
  ingredients: Ingredient[];
  steps: string[];
  servings: number | null;
  prep_minutes: number | null;
  cook_minutes: number | null;
  photo_media_ids: string[];
  best_maker_user_id: string | null;
  best_maker_household_id: string | null;
  tags: string[];
  visibility: RecipeVisibility;
  subgroup_id: string | null;
}

export interface Recipe extends RecipeInput {
  id: string;
  author: { id: string; display_name: string };
  best_maker_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecipePage {
  recipes: Recipe[];
  next_cursor: string | null;
}

export interface RecipeTag {
  tag: string;
  count: number;
}

const BASE = "/api/v1/recipes";

/** @brief Recipes visible to me, optionally searched or filtered by tag. */
export const listRecipes = (p: {
  q?: string;
  tag?: string;
  cursor?: string;
}) => {
  const qs = new URLSearchParams();
  if (p.q) qs.set("q", p.q);
  if (p.tag) qs.set("tag", p.tag);
  if (p.cursor) qs.set("cursor", p.cursor);
  const s = qs.toString();
  return apiGet<RecipePage>(s ? `${BASE}?${s}` : BASE);
};
export const listRecipeTags = () => apiGet<RecipeTag[]>(`${BASE}/tags`);
export const getRecipe = (id: string) => apiGet<Recipe>(`${BASE}/${seg(id)}`);
export const createRecipe = (body: RecipeInput) => apiPost<Recipe>(BASE, body);
export const updateRecipe = (id: string, body: RecipeInput) =>
  apiPut<Recipe>(`${BASE}/${seg(id)}`, body);
export const deleteRecipe = (id: string) => apiDelete(`${BASE}/${seg(id)}`);

/** @brief Request body for adding ingredients to a shopping list. */
export interface ToListInput {
  list_id?: string | null;
  /** Ingredient indexes; omitted = all. */
  ingredients?: number[];
}

/** @brief Add recipe ingredients to a new (no list_id) or existing list. */
export const addToShoppingList = (id: string, body: ToListInput) =>
  apiPost<{ list_id: string; added: number }>(
    `${BASE}/${seg(id)}/shopping-list`,
    body,
  );
