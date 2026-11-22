"use client";
/**
 * @file components/wishlists/WishlistCards.tsx
 * @brief Grid of wishlist hero cards (occasion disc, title, who it's for,
 *        countdown) with an optional "New wishlist" action.
 */
import Link from "next/link";
import { CalendarClock, Gift, Plus } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { useWishlists } from "@/hooks/useWishlists";
import { OCCASIONS, occasionName } from "@/lib/occasions";
import type { Wishlist, WishlistQuery } from "@/lib/api/wishlists";
import { countdown, dayLabel, recipientsText } from "./wishlistText";

function Card({ w }: { w: Wishlist }) {
  const { Icon, tint } = OCCASIONS[w.occasion];
  return (
    <li>
      <Link
        href={`/app/wishlists/${w.id}`}
        className="glass glass-lift relative flex h-full flex-col gap-3 overflow-hidden rounded-[26px] p-5 outline-none focus-visible:outline-2 focus-visible:outline-accent"
      >
        <span
          aria-hidden
          className="pointer-events-none absolute -top-10 -right-10 size-36 rounded-full opacity-25 blur-2xl"
          style={{ background: tint }}
        />
        <span className="flex items-center gap-3">
          <span
            aria-hidden
            className="grid size-11 shrink-0 place-items-center rounded-full text-white shadow-[0_8px_18px_-8px_rgba(0,0,0,0.45)]"
            style={{ background: tint }}
          >
            <Icon className="size-5" />
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="text-xs text-muted">
              {occasionName(w.occasion, w.occasion_label)}
            </span>
            <span className="truncate text-lg leading-tight font-semibold">
              {w.title}
            </span>
          </span>
        </span>
        <span className="text-sm">
          For {recipientsText(w.recipients) || w.owner_name}
        </span>
        <span className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          {w.event_date && (
            <span className="inline-flex items-center gap-1">
              <CalendarClock className="size-3.5" aria-hidden />
              {dayLabel(w.event_date)}, {countdown(w.event_date).toLowerCase()}
            </span>
          )}
          <span>
            {w.item_count} {w.item_count === 1 ? "wish" : "wishes"}
          </span>
        </span>
      </Link>
    </li>
  );
}

/**
 * @brief Wishlist grid.
 * @param query filter (person, household member or creator)
 * @param canCreate show "New wishlist"
 * @param othersOnly hide lists the viewer created
 * @param emptyText text when there are none
 * @return section
 */
export function WishlistCards({
  query = {},
  canCreate = false,
  othersOnly = false,
  emptyText = "No wishlists yet",
}: {
  query?: WishlistQuery;
  canCreate?: boolean;
  othersOnly?: boolean;
  emptyText?: string;
}) {
  const { data, isLoading } = useWishlists(query);
  const lists = (data ?? []).filter((w) => !othersOnly || !w.is_owner);
  return (
    <div className="flex flex-col gap-3">
      {canCreate && (
        <Button asChild size="sm" variant="ghost" className="self-start">
          <Link href="/app/lists/new?type=wishlist">
            <Plus className="size-4" aria-hidden /> New wishlist
          </Link>
        </Button>
      )}
      {isLoading ? (
        <Skeleton height={140} rounded="lg" />
      ) : lists.length === 0 ? (
        <EmptyState compact icon={Gift} title={emptyText} />
      ) : (
        <ul
          aria-label="Wishlists"
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
        >
          {lists.map((w) => (
            <Card key={w.id} w={w} />
          ))}
        </ul>
      )}
    </div>
  );
}
