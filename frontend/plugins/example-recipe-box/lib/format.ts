/**
 * @file lib/format.ts
 * @brief Recipe display helpers.
 */
import type { Recipe } from "../hooks/useRecipes";

const n = (c: number, w: string) => `${c} ${w}${c === 1 ? "" : "s"}`;

/** @brief e.g. "4 ingredients, 3 steps". */
export const summary = (r: Pick<Recipe, "ingredients" | "steps">): string =>
  `${n(r.ingredients.length, "ingredient")}, ${n(r.steps.length, "step")}`;
