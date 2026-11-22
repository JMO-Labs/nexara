"use client";
/**
 * @file components/wishlists/WishlistCards.tsx
 * @brief Grid of wishlist cards with an optional "New wishlist" action,
 *        used on profiles, household pages and /app/wishlists.
 */
import * as React from "react";
import Link from "next/link";
import { Gift, PawPrint, Plus } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { useWishlists } from "@/hooks/useWishlists";
import { OCCASION_LABEL, type Wishlist } from "@/lib/api/wishlists";
import { WishlistEditor } from "./WishlistEditor";

/** @brief "December 12" style date (no year). */
export const occasionDay = (d: string | null) =>
  d
    ? new Date(`${d}T00:00:00`).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
      })
    : null;

function Card({ w }: { w: Wishlist }) {
  const when = occasionDay(w.occasion_date);
  return (
    <li>
      <Link
        href={`/app/wishlists/${w.id}`}
        className="glass glass-lift flex h-full flex-col gap-2 rounded-[24px] p-4 outline-none focus-visible:outline-2 focus-visible:outline-accent"
      >
        <span className="flex items-center gap-2 text-xs text-muted">
          <Gift className="size-3.5 text-[var(--nx-red)]" aria-hidden />
          {OCCASION_LABEL[w.occasion]}
          {when && <span>{when}</span>}
        </span>
        <span className="text-base font-semibold">{w.title}</span>
        <span className="mt-auto flex items-center gap-2 text-sm text-muted">
          {w.household && (
            <span className="inline-flex items-center gap-1">
              {w.household.kind === "pet" && (
                <PawPrint className="size-3.5" aria-hidden />
              )}
              For {w.household.name}
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
 * @param ownerId only this person's lists
 * @param householdId only lists for this household member/pet
 * @param othersOnly hide the viewer's own lists
 * @param canCreate show "New wishlist"
 * @param emptyText text when there are none
 * @return section
 */
export function WishlistCards({
  ownerId,
  householdId,
  canCreate = false,
  othersOnly = false,
  emptyText = "No wishlists yet",
}: {
  ownerId?: string;
  householdId?: string;
  canCreate?: boolean;
  /** Hide the viewer's own lists. */
  othersOnly?: boolean;
  emptyText?: string;
}) {
  const q = {
    ...(ownerId && { owner_id: ownerId }),
    ...(householdId && { household_id: householdId }),
  };
  const { data, isLoading } = useWishlists(q);
  const [editing, setEditing] = React.useState(false);
  const lists = (data ?? []).filter((w) => !othersOnly || !w.is_owner);
  return (
    <div className="flex flex-col gap-3">
      {canCreate && (
        <Button
          size="sm"
          variant="ghost"
          className="self-start"
          onClick={() => setEditing(true)}
        >
          <Plus className="size-4" aria-hidden /> New wishlist
        </Button>
      )}
      {isLoading ? (
        <Skeleton height={120} rounded="lg" />
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
      {editing && (
        <WishlistEditor
          list={null}
          householdId={householdId}
          onClose={() => setEditing(false)}
        />
      )}
    </div>
  );
}
