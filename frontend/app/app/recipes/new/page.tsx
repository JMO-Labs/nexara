/**
 * @file app/app/recipes/new/page.tsx
 * @brief Add a recipe.
 */
"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/ui/page";
import { RecipeForm } from "@/components/recipes/RecipeForm";
import { useFeature } from "@/hooks/useFeature";
import { createRecipe } from "@/lib/api/recipes";

export default function NewRecipeRoute() {
  const on = useFeature("recipes");
  const router = useRouter();
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: createRecipe,
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: ["recipes"] });
      router.push(`/app/recipes/${r.id}`);
    },
  });
  if (!on) return null;
  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-5 pb-8">
      <PageHeader title="Add a recipe" />
      <RecipeForm
        pending={save.isPending}
        error={
          save.isError ? "Could not save the recipe. Please try again." : null
        }
        onSubmit={(b) => save.mutate(b)}
        onCancel={() => router.push("/app/recipes")}
      />
    </div>
  );
}
