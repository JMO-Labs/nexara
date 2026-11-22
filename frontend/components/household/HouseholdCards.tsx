"use client";
/**
 * @file components/household/HouseholdCards.tsx
 * @brief Grid of household member / pet cards linking to their page, with
 *        an optional edit button for the owner.
 */
import Link from "next/link";
import { PawPrint, Pencil, User } from "lucide-react";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { IconButton } from "@/components/ui";
import type { HouseholdMember } from "@/lib/api/household";
import { birthdayText } from "@/lib/profile";

/** @brief Round photo or kind icon. */
export function HouseholdAvatar({
  m,
  className = "size-14",
}: {
  m: Pick<HouseholdMember, "kind" | "photo_media_id" | "name">;
  className?: string;
}) {
  const Icon = m.kind === "pet" ? PawPrint : User;
  return (
    <span
      className={`relative grid shrink-0 place-items-center overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--nx-blue)_18%,transparent)] ${className}`}
    >
      {m.photo_media_id ? (
        <span className="absolute inset-0">
          <MediaThumb mediaId={m.photo_media_id} alt={m.name} />
        </span>
      ) : (
        <Icon className="size-1/2 text-muted" aria-hidden />
      )}
    </span>
  );
}

/** @brief "Dog · Golden retriever" or relation. */
export const householdSubtitle = (m: HouseholdMember) =>
  [m.relation, m.kind === "pet" ? m.species : null, m.breed]
    .filter(Boolean)
    .join(", ");

/**
 * @brief Cards for a list of household members.
 * @param items members
 * @param onEdit show an edit button (owner view)
 * @return list
 */
export function HouseholdCards({
  items,
  onEdit,
}: {
  items: HouseholdMember[];
  onEdit?: (m: HouseholdMember) => void;
}) {
  return (
    <ul
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
      aria-label="Family and pets"
    >
      {items.map((m) => (
        <li key={m.id} className="glass glass-lift relative rounded-[24px]">
          <Link
            href={`/app/household/${m.id}`}
            className="flex items-center gap-3 rounded-[24px] p-3 pr-12 outline-none focus-visible:outline-2 focus-visible:outline-accent"
          >
            <HouseholdAvatar m={m} />
            <span className="min-w-0">
              <span className="block truncate font-medium">{m.name}</span>
              <span className="block truncate text-xs text-muted">
                {householdSubtitle(m) || (m.kind === "pet" ? "Pet" : "Family")}
              </span>
              {m.birthday && (
                <span className="block text-xs text-muted">
                  Born {birthdayText(m.birthday)}
                </span>
              )}
            </span>
          </Link>
          {onEdit && m.can_edit && (
            <IconButton
              aria-label={`Edit ${m.name}`}
              variant="ghost"
              size="sm"
              className="absolute top-1/2 right-2 -translate-y-1/2"
              onClick={() => onEdit(m)}
            >
              <Pencil className="size-4" aria-hidden />
            </IconButton>
          )}
        </li>
      ))}
    </ul>
  );
}
