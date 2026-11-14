"use client";
/**
 * @file components/RecipeBoxWidget.tsx
 * @brief Sidebar widget: recipe of the day and recipe browser launcher.
 */
import { useState } from "react";
import type { PluginComponentProps } from "@/lib/plugins/plugin-loader";
import { useGetRecipes } from "../hooks/useRecipes";
import { summary } from "../lib/format";
import RecipeModal from "./RecipeModal";

/** @brief Deterministic pick of the day from the list. */
function pickOfDay<T>(items: T[]): T | undefined {
  if (!items.length) return undefined;
  return items[Math.floor(Date.now() / 86_400_000) % items.length];
}

export default function RecipeBoxWidget(_props: PluginComponentProps) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useGetRecipes();
  const r = pickOfDay(data?.items ?? []);
  return (
    <section aria-label="Recipe of the day" className="px-3 py-2 text-sm">
      <h3 className="font-semibold">Recipe of the Day</h3>
      {isLoading && <p role="status">Loading…</p>}
      {isError && <p role="alert">Could not load recipes.</p>}
      {!isLoading && !isError && !r && <p>No recipes yet.</p>}
      {r && (
        <div className="mt-1 flex items-center gap-2">
          {r.image_url && (
            // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
            <img
              src={r.image_url}
              alt=""
              className="size-10 rounded object-cover"
            />
          )}
          <div>
            <p className="font-medium">{r.name}</p>
            <p className="text-xs opacity-80">{summary(r)}</p>
          </div>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 underline focus-visible:outline-2 focus-visible:outline-accent"
      >
        Browse recipes
      </button>
      {open && <RecipeModal open onClose={() => setOpen(false)} />}
    </section>
  );
}
