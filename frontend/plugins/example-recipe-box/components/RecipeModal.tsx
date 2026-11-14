"use client";
/**
 * @file components/RecipeModal.tsx
 * @brief Recipe browser: list, search, create, view, delete (owner only).
 */
import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";
import {
  useCurrentUserId,
  useDeleteRecipe,
  useGetRecipes,
  useSearchRecipes,
  type Recipe,
} from "../hooks/useRecipes";
import { summary } from "../lib/format";
import RecipeForm from "./RecipeForm";

type View =
  | { kind: "list" }
  | { kind: "form"; recipe?: Recipe }
  | { kind: "detail"; recipe: Recipe };

export default function RecipeModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [view, setView] = useState<View>({ kind: "list" });
  const [q, setQ] = useState("");
  const all = useGetRecipes();
  const found = useSearchRecipes(q);
  const me = useCurrentUserId().data;
  const del = useDeleteRecipe();
  const confirm = useConfirmDialog((s) => s.confirm);
  const toast = useToasts((s) => s.push);
  const list = q.trim() ? found : all;
  const items = list.data?.items ?? [];
  const back = () => setView({ kind: "list" });

  const remove = async (r: Recipe) => {
    const ok = await confirm({
      title: "Delete recipe",
      message: `Delete "${r.name}"?`,
      tone: "danger",
    });
    if (!ok) return;
    try {
      await del.mutateAsync(r.id);
      back();
    } catch {
      toast({ variant: "danger", message: "Could not delete recipe" });
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Recipe Box" size="lg">
      {view.kind === "form" && (
        <RecipeForm recipe={view.recipe} onDone={back} onCancel={back} />
      )}
      {view.kind === "detail" && (
        <div className="flex flex-col gap-3">
          <h3 className="text-lg font-semibold">{view.recipe.name}</h3>
          <ul className="list-disc pl-5">
            {view.recipe.ingredients.map((i, k) => (
              <li key={k}>
                {[i.qty, i.unit, i.name]
                  .filter((x) => x !== null && x !== "")
                  .join(" ")}
              </li>
            ))}
          </ul>
          <ol className="list-decimal pl-5">
            {view.recipe.steps.map((s, k) => (
              <li key={k}>{s}</li>
            ))}
          </ol>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={back}>
              Back
            </Button>
            {view.recipe.owner_id === me && (
              <>
                <Button
                  variant="outline"
                  onClick={() => setView({ kind: "form", recipe: view.recipe })}
                >
                  Edit
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => remove(view.recipe)}
                >
                  Delete
                </Button>
              </>
            )}
          </div>
        </div>
      )}
      {view.kind === "list" && (
        <div className="flex flex-col gap-3">
          <div className="flex items-end gap-2">
            <Input
              label="Search by name, ingredient or tag"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Button onClick={() => setView({ kind: "form" })}>
              New recipe
            </Button>
          </div>
          {list.isLoading && <p role="status">Loading…</p>}
          {list.isError && <p role="alert">Could not load recipes.</p>}
          {!list.isLoading && !list.isError && items.length === 0 && (
            <p>No recipes found.</p>
          )}
          <ul className="grid gap-3 sm:grid-cols-2">
            {items.map((r) => (
              <li key={r.id} className="rounded-xl border p-3">
                {r.image_url && (
                  // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
                  <img
                    src={r.image_url}
                    alt=""
                    className="mb-2 h-24 w-full rounded object-cover"
                  />
                )}
                <h4 className="font-semibold">{r.name}</h4>
                <p className="text-xs">{summary(r)}</p>
                <p className="text-xs">
                  {r.tags.join(", ")} ·{" "}
                  {new Date(r.created_at).toLocaleDateString()}
                </p>
                <div className="mt-2 flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    aria-label={`View ${r.name}`}
                    onClick={() => setView({ kind: "detail", recipe: r })}
                  >
                    View
                  </Button>
                  {r.owner_id === me && (
                    <Button
                      size="sm"
                      variant="destructive"
                      aria-label={`Delete ${r.name}`}
                      onClick={() => remove(r)}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
}
