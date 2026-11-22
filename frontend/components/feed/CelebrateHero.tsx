/**
 * @file components/feed/CelebrateHero.tsx
 * @brief Banner at the top of a Celebrate post: who and what occasion.
 */
import Link from "next/link";
import { Cake, PartyPopper, PawPrint } from "lucide-react";
import { Avatar } from "@/components/ui";
import type { Celebration } from "@/lib/api/posts";

const OCCASION = {
  birthday: "Happy birthday",
  gotcha_day: "Happy gotcha day",
  milestone: "Celebrating",
} as const;

/** @brief Celebration banner; generic when the viewer can't see the pet. */
export function CelebrateHero({ c }: { c: Celebration }) {
  const Icon =
    c.occasion === "milestone" ? PartyPopper : c.is_pet ? PawPrint : Cake;
  const name = c.name ?? "someone special";
  const photo = c.photo_media_id
    ? `/api/v1/media/${c.photo_media_id}/thumbnail`
    : (c.avatar_url ?? undefined);
  const title = (
    <span className="text-lg font-semibold">
      {OCCASION[c.occasion]}, {name}
    </span>
  );
  return (
    <div className="relative flex items-center gap-3 overflow-hidden rounded-[20px] bg-[color-mix(in_oklab,var(--nx-sun)_18%,transparent)] p-3 pr-4">
      <span className="relative">
        <Avatar src={photo} name={name} size="lg" />
        <span className="absolute -right-1 -bottom-1 grid size-6 place-items-center rounded-full bg-[var(--nx-sun)] text-[var(--nx-bg)]">
          <Icon className="size-3.5" aria-hidden />
        </span>
      </span>
      {c.link ? (
        <Link
          href={c.link}
          className="underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-accent"
        >
          {title}
        </Link>
      ) : (
        title
      )}
    </div>
  );
}
