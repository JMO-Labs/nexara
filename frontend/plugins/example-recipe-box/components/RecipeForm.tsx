"use client";
/**
 * @file components/RecipeForm.tsx
 * @brief Create/edit recipe form with validation and image upload.
 */
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { uploadFile } from "@/lib/api/media";
import { useToasts } from "@/stores/toasts";
import {
  useCreateRecipe,
  useUpdateRecipe,
  type Ingredient,
  type Recipe,
} from "../hooks/useRecipes";

export type FormErrors = {
  name?: string;
  ingredients?: string;
  steps?: string;
};

/**
 * @brief Validate form values.
 * @param v name, ingredients, steps
 * @return map of field errors (empty when valid)
 */
export function validateRecipe(v: {
  name: string;
  ingredients: Ingredient[];
  steps: string[];
}): FormErrors {
  const e: FormErrors = {};
  if (!v.name.trim()) e.name = "Name is required";
  if (!v.ingredients.some((i) => i.name.trim()))
    e.ingredients = "Add at least one ingredient";
  if (!v.steps.some((s) => s.trim())) e.steps = "Add at least one step";
  return e;
}

interface Props {
  recipe?: Recipe;
  onDone: () => void;
  onCancel: () => void;
}

const blank: Ingredient = { name: "", qty: null, unit: "" };

export default function RecipeForm({ recipe, onDone, onCancel }: Props) {
  const [name, setName] = useState(recipe?.name ?? "");
  const [ings, setIngs] = useState<Ingredient[]>(
    recipe?.ingredients.length ? recipe.ingredients : [{ ...blank }],
  );
  const [steps, setSteps] = useState((recipe?.steps ?? []).join("\n"));
  const [tags, setTags] = useState(recipe?.tags ?? []);
  const [tagInput, setTagInput] = useState("");
  const [image, setImage] = useState<string | null>(recipe?.image_url ?? null);
  const [errors, setErrors] = useState<FormErrors>({});
  const [uploading, setUploading] = useState(false);
  const create = useCreateRecipe();
  const update = useUpdateRecipe();
  const toast = useToasts((s) => s.push);
  const pending = create.isPending || update.isPending;

  const setIng = (i: number, p: Partial<Ingredient>) =>
    setIngs((l) => l.map((x, j) => (j === i ? { ...x, ...p } : x)));
  const addTag = () => {
    const t = tagInput.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  };

  const onFile = async (f?: File) => {
    if (!f) return;
    setUploading(true);
    try {
      const m = await uploadFile(f);
      setImage(`/api/v1/media/${m.id}/thumbnail`);
    } catch {
      toast({ variant: "danger", message: "Image upload failed" });
    } finally {
      setUploading(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const stepList = steps
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    const ingredients = ings.filter((i) => i.name.trim());
    const errs = validateRecipe({ name, ingredients, steps: stepList });
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const data = {
      name: name.trim(),
      ingredients,
      steps: stepList,
      tags,
      image_url: image,
    };
    try {
      if (recipe) await update.mutateAsync({ id: recipe.id, data });
      else await create.mutateAsync(data);
      toast({ variant: "success", message: "Recipe saved" });
      onDone();
    } catch {
      toast({ variant: "danger", message: "Could not save recipe" });
    }
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Input
        label="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={errors.name}
        required
      />
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold">Ingredients</legend>
        {ings.map((ing, i) => (
          <div key={i} className="flex flex-wrap items-end gap-2">
            <Input
              label={`Ingredient ${i + 1} name`}
              value={ing.name}
              onChange={(e) => setIng(i, { name: e.target.value })}
            />
            <Input
              label={`Ingredient ${i + 1} quantity`}
              type="number"
              min={0}
              className="w-24"
              value={ing.qty ?? ""}
              onChange={(e) =>
                setIng(i, {
                  qty: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
            <Input
              label={`Ingredient ${i + 1} unit`}
              className="w-24"
              value={ing.unit}
              onChange={(e) => setIng(i, { unit: e.target.value })}
            />
            <Button
              type="button"
              variant="ghost"
              aria-label={`Remove ingredient ${i + 1}`}
              disabled={ings.length === 1}
              onClick={() => setIngs((l) => l.filter((_, j) => j !== i))}
            >
              Remove
            </Button>
          </div>
        ))}
        {errors.ingredients && (
          <p role="alert" className="text-sm text-destructive">
            {errors.ingredients}
          </p>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setIngs([...ings, { ...blank }])}
        >
          Add ingredient
        </Button>
      </fieldset>
      <Textarea
        label="Steps"
        hint="One step per line"
        value={steps}
        onChange={(e) => setSteps(e.target.value)}
        error={errors.steps}
      />
      <div className="flex flex-col gap-2">
        <Input
          label="Add tag"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
          hint="Press Enter to add"
        />
        <ul className="flex flex-wrap gap-2" aria-label="Tags">
          {tags.map((t) => (
            <li key={t}>
              <button
                type="button"
                aria-label={`Remove tag ${t}`}
                onClick={() => setTags(tags.filter((x) => x !== t))}
                className="rounded-full border px-2 text-sm"
              >
                {t} ×
              </button>
            </li>
          ))}
        </ul>
      </div>
      <Input
        label="Image"
        type="file"
        accept="image/*"
        onChange={(e) => onFile(e.target.files?.[0])}
        hint={uploading ? "Uploading…" : image ? "Image attached" : undefined}
      />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={pending} disabled={uploading}>
          Save
        </Button>
      </div>
    </form>
  );
}
