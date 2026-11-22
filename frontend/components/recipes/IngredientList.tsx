/**
 * @file components/recipes/IngredientList.tsx
 * @brief Ingredients with local-only checkboxes (nothing is saved).
 */
"use client";

import * as React from "react";
import type { Ingredient } from "@/lib/api/recipes";

/**
 * @param ingredients lines to show
 * @return checklist
 */
export function IngredientList({ ingredients }: { ingredients: Ingredient[] }) {
  const [done, setDone] = React.useState<Set<number>>(new Set());
  const toggle = (i: number) =>
    setDone((s) => {
      const n = new Set(s);
      if (!n.delete(i)) n.add(i);
      return n;
    });
  return (
    <ul className="m-0 flex list-none flex-col gap-1 p-0">
      {ingredients.map((ing, i) => (
        <li key={i}>
          <label className="flex min-h-9 cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={done.has(i)}
              onChange={() => toggle(i)}
              className="accent-accent size-4"
            />
            <span className={done.has(i) ? "text-muted line-through" : ""}>
              {ing.qty ? `${ing.qty} ` : ""}
              {ing.item}
            </span>
          </label>
        </li>
      ))}
    </ul>
  );
}
