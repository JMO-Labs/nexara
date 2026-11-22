/**
 * @file components/recipes/RecipeView.tsx
 * @brief Recipe detail: story first, then ingredients and numbered steps.
 */
import { Chip } from "@/components/ui";
import { mediaFileUrl } from "@/lib/api/media";
import type { Recipe } from "@/lib/api/recipes";
import { IngredientList } from "./IngredientList";

const mins = (n: number | null, label: string) =>
  n ? `${label} ${n} min` : null;

/**
 * @param recipe recipe to render
 * @return article
 */
export function RecipeView({ recipe }: { recipe: Recipe }) {
  const meta = [
    recipe.servings ? `Serves ${recipe.servings}` : null,
    mins(recipe.prep_minutes, "Prep"),
    mins(recipe.cook_minutes, "Cook"),
  ].filter(Boolean);
  return (
    <article className="glass flex flex-col gap-5 rounded-3xl p-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{recipe.title}</h1>
        <p className="text-muted text-sm">
          Added by {recipe.author.display_name}
          {meta.length > 0 && ` · ${meta.join(" · ")}`}
        </p>
        {recipe.best_maker_name && (
          <p className="mt-1">
            <Chip>Made best by {recipe.best_maker_name}</Chip>
          </p>
        )}
      </header>
      {recipe.photo_media_ids.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-2 gap-2 p-0 sm:grid-cols-3">
          {recipe.photo_media_ids.map((id) => (
            <li key={id}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={mediaFileUrl(id)}
                alt={`Photo of ${recipe.title}`}
                className="aspect-square w-full rounded-xl object-cover"
              />
            </li>
          ))}
        </ul>
      )}
      {recipe.story && <p className="whitespace-pre-wrap">{recipe.story}</p>}
      {recipe.ingredients.length > 0 && (
        <section aria-labelledby="ing-h" className="flex flex-col gap-2">
          <h2 id="ing-h" className="text-lg font-semibold">
            Ingredients
          </h2>
          <IngredientList ingredients={recipe.ingredients} />
        </section>
      )}
      {recipe.steps.length > 0 && (
        <section aria-labelledby="steps-h" className="flex flex-col gap-2">
          <h2 id="steps-h" className="text-lg font-semibold">
            Steps
          </h2>
          <ol className="m-0 flex list-decimal flex-col gap-2 pl-6">
            {recipe.steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </section>
      )}
      {recipe.tags.length > 0 && (
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {recipe.tags.map((t) => (
            <li key={t}>
              <Chip>{t}</Chip>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
