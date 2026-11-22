/**
 * @file app/app/recipes/page.tsx
 * @brief Recipe book: search, tag filter and a grid of cards.
 */
"use client";

import * as React from "react";
import Link from "next/link";
import { ChefHat } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button, EmptyState, Input } from "@/components/ui";
import { PageHeader } from "@/components/ui/page";
import { RecipeCard } from "@/components/recipes/RecipeCard";
import { useFeature } from "@/hooks/useFeature";
import { listRecipes, listRecipeTags } from "@/lib/api/recipes";

export default function RecipesRoute() {
  const on = useFeature("recipes");
  const [q, setQ] = React.useState("");
  const [tag, setTag] = React.useState<string | undefined>();
  const { data } = useQuery({
    queryKey: ["recipes", { q, tag }],
    queryFn: () => listRecipes({ q: q.trim() || undefined, tag }),
    enabled: on,
  });
  const { data: tags = [] } = useQuery({
    queryKey: ["recipes", "tags"],
    queryFn: listRecipeTags,
    enabled: on,
  });
  if (!on) return null;
  const filtered = q.trim() !== "" || tag !== undefined;
  return (
    <div className="mx-auto flex w-full max-w-[1000px] flex-col gap-5 pb-8">
      <PageHeader
        title="Recipes"
        description="The dishes your family keeps coming back to."
        actions={
          <Button asChild>
            <Link href="/app/recipes/new">Add a recipe</Link>
          </Button>
        }
      />
      <Input
        type="search"
        label="Search recipes"
        placeholder="Title, story or ingredient"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {tags.length > 0 && (
        <ul
          className="m-0 flex list-none flex-wrap gap-2 p-0"
          aria-label="Filter by tag"
        >
          {tags.map((t) => (
            <li key={t.tag}>
              <button
                type="button"
                aria-pressed={tag === t.tag}
                onClick={() => setTag(tag === t.tag ? undefined : t.tag)}
                className="glass-item focus-visible:outline-accent rounded-full px-3 py-1 text-sm focus-visible:outline-2 aria-pressed:font-semibold aria-pressed:underline"
              >
                {t.tag} ({t.count})
              </button>
            </li>
          ))}
        </ul>
      )}
      {data && data.recipes.length === 0 && (
        <EmptyState
          icon={ChefHat}
          title={
            filtered
              ? "No recipes match"
              : "No recipes yet. Add the one everyone asks for."
          }
        />
      )}
      <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 md:grid-cols-3">
        {data?.recipes.map((r) => (
          <li key={r.id}>
            <RecipeCard recipe={r} />
          </li>
        ))}
      </ul>
    </div>
  );
}
