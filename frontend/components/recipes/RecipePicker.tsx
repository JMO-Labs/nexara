"use client";
/**
 * @file components/recipes/RecipePicker.tsx
 * @brief "Link a recipe" control for list items: search recipes by text and
 *        pick one, or unlink. Hidden when the recipes feature is off.
 */
import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Button, Input } from "@/components/ui";
import { useFeature } from "@/hooks/useFeature";
import { getRecipe, listRecipes } from "@/lib/api/recipes";

/**
 * @param value linked recipe id or null
 * @param onChange called with the picked id, or null to unlink
 * @return control, or null when the feature is off
 */
export function RecipePicker({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (id: string | null) => void;
}) {
  const on = useFeature("recipes");
  const [q, setQ] = React.useState("");
  const linked = useQuery({
    queryKey: ["recipes", value],
    queryFn: () => getRecipe(value!),
    enabled: on && !!value,
    retry: false,
  });
  const found = useQuery({
    queryKey: ["recipes", { q, tag: undefined }],
    queryFn: () => listRecipes({ q: q.trim() }),
    enabled: on && !value && q.trim().length > 1,
  });
  if (!on) return null;
  if (value) {
    return (
      <div className="flex flex-col gap-1">
        <span className="text-sm font-semibold">Recipe</span>
        <div className="flex items-center gap-2">
          <Link
            href={`/app/recipes/${value}`}
            className="focus-visible:outline-accent underline focus-visible:outline-2"
          >
            {linked.data?.title ?? "View recipe"}
          </Link>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onChange(null)}
          >
            Unlink recipe
          </Button>
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <Input
        type="search"
        label="Link a recipe"
        placeholder="Search recipes"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {found.data && (
        <ul
          aria-label="Matching recipes"
          className="m-0 flex list-none flex-col p-0"
        >
          {found.data.recipes.length === 0 && (
            <li className="text-muted text-sm">No recipes match.</li>
          )}
          {found.data.recipes.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => {
                  onChange(r.id);
                  setQ("");
                }}
                className="focus-visible:outline-accent w-full rounded-lg px-2 py-2 text-left hover:bg-[var(--nx-item)] focus-visible:outline-2"
              >
                {r.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
