/**
 * @file hooks/useRecipes.ts
 * @brief TanStack Query hooks for the recipe box plugin API.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete, seg } from "@/lib/api/client";
import { getMe } from "@/lib/api/users";

const BASE = "/api/v1/plugins/example-recipe-box/recipes";
const KEY = ["plugin", "example-recipe-box", "recipes"] as const;

export interface Ingredient {
  name: string;
  qty: number | null;
  unit: string;
}
export interface RecipeInput {
  name: string;
  ingredients: Ingredient[];
  steps: string[];
  tags: string[];
  image_url?: string | null;
}
export interface Recipe extends RecipeInput {
  id: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}
interface Page {
  items: Recipe[];
  total: number;
}

/** @brief List recipes, optionally filtered by tag. */
export const useGetRecipes = (tag_filter?: string) =>
  useQuery({
    queryKey: [...KEY, "list", tag_filter ?? ""],
    queryFn: () =>
      apiGet<Page>(
        tag_filter ? `${BASE}?tag=${encodeURIComponent(tag_filter)}` : BASE,
      ),
  });

/** @brief Fetch one recipe. */
export const useGetRecipe = (recipe_id: string | null) =>
  useQuery({
    queryKey: [...KEY, "one", recipe_id],
    queryFn: () => apiGet<Recipe>(`${BASE}/${seg(recipe_id as string)}`),
    enabled: !!recipe_id,
  });

/** @brief Search recipes by name or ingredient. */
export const useSearchRecipes = (query: string) =>
  useQuery({
    queryKey: [...KEY, "search", query],
    queryFn: () =>
      apiGet<Page>(`${BASE}/search?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length > 0,
  });

function useInvalidating<V, R>(fn: (v: V) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** @brief Create a recipe; mutate(recipe_data). */
export const useCreateRecipe = () =>
  useInvalidating((data: RecipeInput) => apiPost<Recipe>(BASE, data));

/** @brief Update a recipe; mutate({ id, data }). */
export const useUpdateRecipe = () =>
  useInvalidating(({ id, data }: { id: string; data: RecipeInput }) =>
    apiPut<Recipe>(`${BASE}/${seg(id)}`, data),
  );

/** @brief Delete a recipe; mutate(recipe_id). */
export const useDeleteRecipe = () =>
  useInvalidating((id: string) => apiDelete(`${BASE}/${seg(id)}`));

/** @brief Current user id (for owner-only actions). */
export const useCurrentUserId = () =>
  useQuery({
    queryKey: ["plugin", "example-recipe-box", "me"],
    queryFn: getMe,
    select: (u) => u.id,
    staleTime: 60_000,
  });
