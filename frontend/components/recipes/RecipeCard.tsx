/**
 * @file components/recipes/RecipeCard.tsx
 * @brief Grid card: photo, title and who makes it best.
 */
import Link from "next/link";
import { ChefHat } from "lucide-react";
import { mediaFileUrl } from "@/lib/api/media";
import type { Recipe } from "@/lib/api/recipes";

/**
 * @param recipe recipe to show
 * @return link card
 */
export function RecipeCard({ recipe }: { recipe: Recipe }) {
  const photo = recipe.photo_media_ids[0];
  return (
    <Link
      href={`/app/recipes/${recipe.id}`}
      className="glass-item focus-visible:outline-accent flex flex-col overflow-hidden rounded-2xl focus-visible:outline-2"
    >
      {photo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={mediaFileUrl(photo)}
          alt=""
          className="aspect-[4/3] w-full object-cover"
        />
      ) : (
        <div
          aria-hidden
          className="text-muted flex aspect-[4/3] w-full items-center justify-center"
        >
          <ChefHat className="size-10" />
        </div>
      )}
      <div className="flex flex-col gap-0.5 p-3">
        <span className="font-semibold">{recipe.title}</span>
        {recipe.best_maker_name && (
          <span className="text-muted text-sm">
            Made best by {recipe.best_maker_name}
          </span>
        )}
      </div>
    </Link>
  );
}
