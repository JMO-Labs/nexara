/**
 * @file tests/unit/lib/recipes-api.test.ts
 * @brief Recipe client hits versioned /api/v1/recipes paths.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";

const m = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  ...m,
}));

import {
  createRecipe,
  deleteRecipe,
  getRecipe,
  listRecipes,
  listRecipeTags,
  updateRecipe,
  type RecipeInput,
} from "@/lib/api/recipes";

describe("recipes api", () => {
  beforeEach(() => vi.clearAllMocks());
  it("uses /api/v1/recipes paths", () => {
    const body = {} as RecipeInput;
    listRecipes({});
    listRecipes({ q: "corn bread", tag: "dinner" });
    listRecipeTags();
    getRecipe("r1");
    createRecipe(body);
    updateRecipe("r1", body);
    deleteRecipe("r1");
    expect(m.apiGet.mock.calls.map((c) => c[0])).toEqual([
      "/api/v1/recipes",
      "/api/v1/recipes?q=corn+bread&tag=dinner",
      "/api/v1/recipes/tags",
      "/api/v1/recipes/r1",
    ]);
    expect(m.apiPost).toHaveBeenCalledWith("/api/v1/recipes", body);
    expect(m.apiPut).toHaveBeenCalledWith("/api/v1/recipes/r1", body);
    expect(m.apiDelete).toHaveBeenCalledWith("/api/v1/recipes/r1");
  });
});
