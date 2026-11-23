"use client";
/**
 * @file components/recipes/AddToListDialog.tsx
 * @brief "Add to shopping list" button + dialog: pick ingredients, then a
 *        new list or one of the viewer's own active lists.
 */
import * as React from "react";
import { ShoppingCart } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button, Modal, Option, Select } from "@/components/ui";
import { useLists } from "@/hooks/useLists";
import { addToShoppingList, type Recipe } from "@/lib/api/recipes";
import { useSession } from "@/stores/session";
import { useToasts } from "@/stores/toasts";

/**
 * @param recipe recipe whose ingredients are offered
 * @return trigger button and modal
 */
export function AddToListDialog({ recipe }: { recipe: Recipe }) {
  const router = useRouter();
  const user = useSession((s) => s.user);
  const push = useToasts((s) => s.push);
  const [open, setOpen] = React.useState(false);
  const [picked, setPicked] = React.useState<boolean[]>(() =>
    recipe.ingredients.map(() => true),
  );
  const [mode, setMode] = React.useState<"new" | "existing">("new");
  const [listId, setListId] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { data } = useLists(user?.community_id, 100);
  const mine = (data?.lists ?? []).filter(
    (l) => l.ownerId === user?.id && l.status === "active",
  );
  const idx = picked.flatMap((p, i) => (p ? [i] : []));
  const ready = idx.length > 0 && (mode === "new" || Boolean(listId));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await addToShoppingList(recipe.id, {
        list_id: mode === "existing" ? listId : null,
        ingredients: idx,
      });
      push({
        variant: "success",
        message: `Added ${r.added} items`,
        action: {
          label: "View list",
          onClick: () => router.push(`/app/lists/${r.list_id}`),
        },
      });
      setOpen(false);
    } catch {
      setError("Couldn't add to the list. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        type="button"
        className="min-h-11 self-start"
        onClick={() => setOpen(true)}
      >
        <ShoppingCart aria-hidden className="size-4" /> Add to shopping list
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Add to shopping list"
        footer={
          <Button
            className="min-h-11"
            onClick={submit}
            disabled={!ready || busy}
          >
            Add
          </Button>
        }
      >
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="mb-1 font-semibold">Ingredients</legend>
          {recipe.ingredients.map((ing, i) => (
            <label key={i} className="flex min-h-11 items-center gap-2">
              <input
                type="checkbox"
                className="size-5"
                checked={picked[i]}
                onChange={(e) =>
                  setPicked(
                    picked.map((p, j) => (j === i ? e.target.checked : p)),
                  )
                }
              />
              {`${ing.qty} ${ing.item}`.trim()}
            </label>
          ))}
        </fieldset>
        <fieldset className="m-0 mt-4 flex flex-col gap-2 border-0 p-0">
          <legend className="mb-1 font-semibold">Destination</legend>
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="radio"
              name="dest"
              className="size-5"
              checked={mode === "new"}
              onChange={() => setMode("new")}
            />
            New shopping list
          </label>
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="radio"
              name="dest"
              className="size-5"
              checked={mode === "existing"}
              onChange={() => setMode("existing")}
            />
            Add to an existing list
          </label>
          {mode === "existing" && (
            <Select
              label="Choose a list"
              placeholder="Choose a list"
              value={listId}
              onValueChange={setListId}
            >
              {mine.map((l) => (
                <Option key={l.id} value={l.id}>
                  {l.title}
                </Option>
              ))}
            </Select>
          )}
        </fieldset>
        {error && (
          <p role="alert" className="mt-2 text-sm text-danger">
            {error}
          </p>
        )}
      </Modal>
    </>
  );
}
