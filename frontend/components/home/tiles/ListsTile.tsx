"use client";
/**
 * @file components/home/tiles/ListsTile.tsx
 * @brief Lists tile: three most recently updated lists with progress bars.
 */
import Link from "next/link";
import { ListChecks } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { useCommunityId } from "@/hooks/useCommunityId";
import { useLists } from "@/hooks/useLists";

/**
 * @brief Lists tile.
 * @param props open/onToggle from the home page
 * @return HomeTile
 */
export function ListsTile({ open, onToggle }: TileSlotProps) {
  const { data } = useLists(useCommunityId());
  const lists = [...(data?.lists ?? [])]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 3);
  return (
    <HomeTile
      id="lists"
      title="Lists"
      icon={ListChecks}
      href="/app/inbox?view=lists"
      linkLabel="All lists"
      summary={lists[0]?.title ?? "No lists yet"}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:lists]"
    >
      {lists.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <p className="text-sm text-[var(--nx-muted)]">No lists yet</p>
          <Link href="/app/lists/new" className="text-sm underline">
            Start a list
          </Link>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {lists.map((l) => {
            const pct = l.itemCount
              ? Math.round((l.completedCount / l.itemCount) * 100)
              : 0;
            return (
              <li key={l.id}>
                <Link
                  href={`/app/inbox?view=lists&item=${l.id}`}
                  className="block"
                >
                  <span className="flex items-baseline gap-2 text-sm">
                    <span
                      aria-hidden
                      className="size-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: l.color ?? "var(--nx-blue)" }}
                    />
                    <span className="min-w-0 flex-1 truncate font-medium">
                      {l.title}
                    </span>
                    <span className="text-xs tabular-nums text-[var(--nx-muted)]">
                      {l.completedCount}/{l.itemCount}
                    </span>
                  </span>
                  <span
                    role="progressbar"
                    aria-label={`${l.title} progress`}
                    aria-valuenow={pct}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)]"
                  >
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: l.color ?? "var(--nx-blue)",
                      }}
                    />
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </HomeTile>
  );
}
