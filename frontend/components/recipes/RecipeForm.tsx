"use client";
/**
 * @file components/recipes/RecipeForm.tsx
 * @brief Create or edit a recipe: story, ingredient rows, steps, photos,
 *        best maker, tags and who can see it.
 */
import * as React from "react";
import { Plus, X } from "lucide-react";
import { Button, Input, Textarea } from "@/components/ui";
import { Field, selectCls } from "@/components/wishlists/wizard/fields";
import {
  MediaTray,
  useMediaUploads,
} from "@/components/feed/ComposerAttachments";
import { useMembersList } from "@/hooks/useMembersList";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import { mediaFileUrl } from "@/lib/api/media";
import type {
  Ingredient,
  Recipe,
  RecipeInput,
  RecipeVisibility,
} from "@/lib/api/recipes";
import { toInput } from "./recipeInput";

/**
 * @param initial recipe being edited, omit to create
 * @param pending save in flight
 * @param error message to show
 * @param onSubmit receives the API body
 * @param onCancel cancel handler
 * @return form
 */
export function RecipeForm({
  initial,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  initial?: Recipe;
  pending?: boolean;
  error?: string | null;
  onSubmit: (body: RecipeInput) => void;
  onCancel: () => void;
}) {
  const { data: members = [] } = useMembersList();
  const { data: groups = [] } = useSubgroupList();
  const { data: household = [] } = useVisibleHousehold();
  const uploads = useMediaUploads();
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [title, setTitle] = React.useState(initial?.title ?? "");
  const [story, setStory] = React.useState(initial?.story ?? "");
  const [ingredients, setIngredients] = React.useState<Ingredient[]>(
    initial?.ingredients.length ? initial.ingredients : [{ qty: "", item: "" }],
  );
  const [steps, setSteps] = React.useState<string[]>(
    initial?.steps.length ? initial.steps : [""],
  );
  const [servings, setServings] = React.useState(
    String(initial?.servings ?? ""),
  );
  const [prep, setPrep] = React.useState(String(initial?.prep_minutes ?? ""));
  const [cook, setCook] = React.useState(String(initial?.cook_minutes ?? ""));
  const [kept, setKept] = React.useState(initial?.photo_media_ids ?? []);
  const [maker, setMaker] = React.useState(
    initial?.best_maker_user_id
      ? `user:${initial.best_maker_user_id}`
      : initial?.best_maker_household_id
        ? `household:${initial.best_maker_household_id}`
        : "",
  );
  const [tags, setTags] = React.useState((initial?.tags ?? []).join(", "));
  const [visibility, setVisibility] = React.useState<RecipeVisibility>(
    initial?.visibility ?? "community",
  );
  const [subgroup, setSubgroup] = React.useState(initial?.subgroup_id ?? "");
  const [localErr, setLocalErr] = React.useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return setLocalErr("Add a title.");
    if (visibility === "subgroup" && !subgroup)
      return setLocalErr("Pick a group.");
    setLocalErr(null);
    onSubmit(
      toInput({
        title,
        story,
        ingredients,
        steps,
        servings,
        prep,
        cook,
        photos: [...kept, ...uploads.readyIds],
        maker,
        tags,
        visibility,
        subgroup,
      }),
    );
  };
  const shown = localErr ?? error;
  const numCls = `${selectCls} w-28`;

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Field label="Title">
        <Input
          value={title}
          maxLength={120}
          onChange={(e) => setTitle(e.target.value)}
        />
      </Field>
      <Field
        label="The story"
        hint="Who made it, and when you ate it. Use @ to mention someone."
      >
        <Textarea
          rows={4}
          value={story}
          onChange={(e) => setStory(e.target.value)}
        />
      </Field>
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Ingredients</legend>
        {ingredients.map((ing, i) => (
          <div key={i} className="flex items-center gap-2">
            <Input
              aria-label={`Amount ${i + 1}`}
              placeholder="2 cups"
              className="w-28"
              value={ing.qty}
              maxLength={40}
              onChange={(e) =>
                setIngredients(
                  ingredients.map((x, j) =>
                    j === i ? { ...x, qty: e.target.value } : x,
                  ),
                )
              }
            />
            <Input
              aria-label={`Ingredient ${i + 1}`}
              placeholder="Cornmeal"
              value={ing.item}
              maxLength={200}
              onChange={(e) =>
                setIngredients(
                  ingredients.map((x, j) =>
                    j === i ? { ...x, item: e.target.value } : x,
                  ),
                )
              }
            />
            <button
              type="button"
              aria-label={`Remove ingredient ${i + 1}`}
              className="focus-visible:outline-accent rounded-full p-2 focus-visible:outline-2"
              onClick={() =>
                setIngredients(ingredients.filter((_, j) => j !== i))
              }
            >
              <X aria-hidden className="size-4" />
            </button>
          </div>
        ))}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="self-start"
          disabled={ingredients.length >= 100}
          onClick={() =>
            setIngredients([...ingredients, { qty: "", item: "" }])
          }
        >
          <Plus aria-hidden className="size-4" /> Add ingredient
        </Button>
      </fieldset>
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Steps</legend>
        {steps.map((s, i) => (
          <div key={i} className="flex items-start gap-2">
            <Textarea
              aria-label={`Step ${i + 1}`}
              rows={2}
              value={s}
              onChange={(e) =>
                setSteps(steps.map((x, j) => (j === i ? e.target.value : x)))
              }
            />
            <button
              type="button"
              aria-label={`Remove step ${i + 1}`}
              className="focus-visible:outline-accent rounded-full p-2 focus-visible:outline-2"
              onClick={() => setSteps(steps.filter((_, j) => j !== i))}
            >
              <X aria-hidden className="size-4" />
            </button>
          </div>
        ))}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="self-start"
          disabled={steps.length >= 60}
          onClick={() => setSteps([...steps, ""])}
        >
          <Plus aria-hidden className="size-4" /> Add step
        </Button>
      </fieldset>
      <div className="flex flex-wrap gap-3">
        <Field label="Servings">
          <input
            type="number"
            min={1}
            className={numCls}
            value={servings}
            onChange={(e) => setServings(e.target.value)}
          />
        </Field>
        <Field label="Prep (min)">
          <input
            type="number"
            min={0}
            className={numCls}
            value={prep}
            onChange={(e) => setPrep(e.target.value)}
          />
        </Field>
        <Field label="Cook (min)">
          <input
            type="number"
            min={0}
            className={numCls}
            value={cook}
            onChange={(e) => setCook(e.target.value)}
          />
        </Field>
      </div>
      <div className="flex flex-col gap-2">
        {kept.length > 0 && (
          <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
            {kept.map((id) => (
              <li key={id} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={mediaFileUrl(id)}
                  alt="Recipe photo"
                  className="size-16 rounded-lg object-cover"
                />
                <button
                  type="button"
                  aria-label="Remove photo"
                  className="bg-surface focus-visible:outline-accent absolute -top-1 -right-1 rounded-full p-0.5 focus-visible:outline-2"
                  onClick={() => setKept(kept.filter((k) => k !== id))}
                >
                  <X aria-hidden className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <MediaTray items={uploads.items} onRemove={uploads.remove} />
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          aria-label="Choose photos"
          onChange={(e) => {
            uploads.add(e.target.files);
            e.target.value = "";
          }}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="self-start"
          disabled={kept.length + uploads.items.length >= 10}
          onClick={() => fileRef.current?.click()}
        >
          Add photos
        </Button>
      </div>
      <Field label="Made best by">
        <select
          className={selectCls}
          value={maker}
          onChange={(e) => setMaker(e.target.value)}
        >
          <option value="">Nobody in particular</option>
          <optgroup label="People">
            {members.map((m) => (
              <option key={m.id} value={`user:${m.id}`}>
                {m.display_name}
              </option>
            ))}
          </optgroup>
          <optgroup label="Household">
            {household.map((h) => (
              <option key={h.id} value={`household:${h.id}`}>
                {h.name}
              </option>
            ))}
          </optgroup>
        </select>
      </Field>
      <Field label="Tags" hint="Separate with commas, up to 10.">
        <Input value={tags} onChange={(e) => setTags(e.target.value)} />
      </Field>
      <Field label="Who can see it">
        <select
          className={selectCls}
          value={visibility}
          onChange={(e) => setVisibility(e.target.value as RecipeVisibility)}
        >
          <option value="community">Everyone</option>
          <option value="subgroup">A group</option>
          <option value="private">Only me</option>
        </select>
      </Field>
      {visibility === "subgroup" && (
        <Field label="Group">
          <select
            className={selectCls}
            value={subgroup}
            onChange={(e) => setSubgroup(e.target.value)}
          >
            <option value="">Pick a group</option>
            {groups
              .filter((g) => g.is_member)
              .map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
          </select>
        </Field>
      )}
      {shown && (
        <p role="alert" className="text-danger text-sm">
          {shown}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={pending} disabled={uploads.busy}>
          Save recipe
        </Button>
      </div>
    </form>
  );
}
