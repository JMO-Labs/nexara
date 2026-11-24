"use client";
/**
 * @file components/home/tiles/OnThisDayTile.tsx
 * @brief On this day: posts and photos from this date in past years, grouped
 *        by "N years ago". Renders nothing when there is nothing to show or
 *        the feature is off.
 */
import { NsfwCover } from "@/components/feed/NsfwCover";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { useFeature } from "@/hooks/useFeature";
import { getOnThisDay } from "@/lib/api/memories";
import type { Post } from "@/lib/api/posts";

const ago = (n: number) => (n === 1 ? "1 year ago" : `${n} years ago`);

/**
 * @brief On this day tile.
 * @param props open/onToggle from the home page
 * @return HomeTile, or null when empty
 */
export function OnThisDayTile({ open, onToggle }: TileSlotProps) {
  const on = useFeature("on_this_day");
  const { data } = useQuery({
    queryKey: ["memories", "on-this-day"],
    queryFn: getOnThisDay,
    staleTime: 10 * 60_000,
    enabled: on,
  });
  if (!on || !data || data.items.length === 0) return null;

  const groups = new Map<number, Post[]>();
  data.items.forEach((p, i) => {
    const n = data.years_ago[i] ?? 0;
    groups.set(n, [...(groups.get(n) ?? []), p]);
  });
  const years = [...groups.keys()].sort((a, b) => a - b);

  return (
    <HomeTile
      id="memories"
      title="On this day"
      icon={History}
      href="/app?memories=1"
      linkLabel="Today"
      summary={`${data.items.length} ${data.items.length === 1 ? "memory" : "memories"}`}
      count={data.items.length}
      open={open}
      onToggle={onToggle}
    >
      <div className="flex flex-col gap-3">
        {years.map((n) => (
          <section key={n} aria-label={ago(n)}>
            <h3 className="mb-1.5 text-sm font-medium text-[var(--nx-muted)]">
              {ago(n)}
            </h3>
            <ul className="flex flex-col gap-1.5">
              {groups.get(n)!.map((p) => {
                const photo = p.media.find((m) =>
                  m.mime_type.startsWith("image/"),
                );
                return (
                  <li key={p.id}>
                    <NsfwCover
                      nsfw={p.is_nsfw || photo?.is_nsfw}
                      itemId={`post:${p.id}`}
                      compact
                      hideWhenCovered
                      className="rounded-[20px]"
                    >
                      <Link
                        href={`/app/post/${p.id}`}
                        className="glass-item flex items-center gap-3 rounded-[20px] p-2 outline-none focus-visible:outline-2 focus-visible:outline-accent"
                      >
                        {photo ? (
                          // eslint-disable-next-line @next/next/no-img-element -- API-served thumbnails, not optimizable by next/image
                          <img
                            src={photo.thumbnail_url ?? photo.url}
                            alt=""
                            loading="lazy"
                            className="size-12 shrink-0 rounded-xl object-cover"
                          />
                        ) : null}
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">
                            {p.author.display_name}
                          </span>
                          <span className="block truncate text-sm text-[var(--nx-muted)]">
                            {p.content ||
                              (photo ? "Shared a photo" : "Shared a post")}
                          </span>
                        </span>
                      </Link>
                    </NsfwCover>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </HomeTile>
  );
}
