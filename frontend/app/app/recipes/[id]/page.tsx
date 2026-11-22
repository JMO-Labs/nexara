/**
 * @file app/app/recipes/[id]/page.tsx
 * @brief One recipe, with edit and delete for the author or an admin.
 */
"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import { RecipeForm } from "@/components/recipes/RecipeForm";
import { RecipeView } from "@/components/recipes/RecipeView";
import { useFeature } from "@/hooks/useFeature";
import { deleteRecipe, getRecipe, updateRecipe } from "@/lib/api/recipes";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useSession } from "@/stores/session";

export default function RecipeRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const on = useFeature("recipes");
  const user = useSession((s) => s.user);
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const { data, isError } = useQuery({
    queryKey: ["recipes", id],
    queryFn: () => getRecipe(id),
    enabled: on,
    retry: false,
  });
  const save = useMutation({
    mutationFn: (b: Parameters<typeof updateRecipe>[1]) => updateRecipe(id, b),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["recipes"] });
      setEditing(false);
    },
  });
  const del = useMutation({
    mutationFn: () => deleteRecipe(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["recipes"] });
      router.push("/app/recipes");
    },
  });
  if (!on) return null;
  if (isError) return <p role="alert">This recipe is not available.</p>;
  if (!data) return null;
  const canEdit = data.author.id === user?.id || user?.role === "admin";
  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4 pb-8">
      {editing ? (
        <RecipeForm
          initial={data}
          pending={save.isPending}
          error={
            save.isError ? "Could not save the recipe. Please try again." : null
          }
          onSubmit={(b) => save.mutate(b)}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <>
          <RecipeView recipe={data} />
          {canEdit && (
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setEditing(true)}>
                Edit
              </Button>
              <Button
                variant="ghost"
                loading={del.isPending}
                onClick={async () => {
                  const ok = await useConfirmDialog.getState().confirm({
                    title: "Delete this recipe?",
                    message: "It will also be unlinked from any list items.",
                    confirmLabel: "Delete",
                    tone: "danger",
                  });
                  if (ok) del.mutate();
                }}
              >
                Delete
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
