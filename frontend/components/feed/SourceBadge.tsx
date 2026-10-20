"use client";
/**
 * @file components/feed/SourceBadge.tsx
 * @brief Pill badge showing the source of a post (community or subgroup).
 *        Community posts show a neutral "Community" pill; subgroup posts
 *        show the subgroup name as an accent pill linking to the group page.
 * @param subgroupId   Subgroup UUID or null for community posts.
 * @param subgroupName Human-readable subgroup name.
 * @param subgroupSlug URL slug for the subgroup. When absent the badge renders
 *                     as a non-clickable span to avoid UUID 404s.
 */
import * as React from "react";
import Link from "next/link";

export interface SourceBadgeProps {
  subgroupId: string | null;
  subgroupName: string | null;
  subgroupSlug?: string | null;
}

export function SourceBadge({
  subgroupId,
  subgroupName,
  subgroupSlug,
}: SourceBadgeProps) {
  if (!subgroupId) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
        aria-label="Posted in Community"
      >
        Community
      </span>
    );
  }

  const name = subgroupName ?? "Subgroup";

  if (!subgroupSlug) {
    // Slug unavailable — render non-clickable badge to avoid UUID 404s.
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
        aria-label={`Posted in ${name}`}
      >
        {name}
      </span>
    );
  }

  const href = `/app/subgroups/${subgroupSlug}`;

  return (
    <Link
      href={href}
      aria-label={`Posted in ${name}`}
      onClick={(e) => e.stopPropagation()}
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800/50 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
    >
      {name}
    </Link>
  );
}

export default SourceBadge;
