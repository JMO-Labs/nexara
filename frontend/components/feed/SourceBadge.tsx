"use client";
/**
 * @file components/feed/SourceBadge.tsx
 * @brief Pill showing a post's source: neutral "Community" or the subgroup
 *        name (linked to the group page when a slug is known).
 * @param subgroupId   Subgroup UUID or null for community posts.
 * @param subgroupName Human-readable subgroup name.
 * @param subgroupSlug URL slug; when absent the badge is not clickable
 *                     (avoids UUID 404s).
 */
import * as React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui";

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
    return <Badge aria-label="Posted in Community">Community</Badge>;
  }
  const name = subgroupName ?? "Subgroup";
  if (!subgroupSlug) {
    return (
      <Badge tone="accent" aria-label={`Posted in ${name}`}>
        {name}
      </Badge>
    );
  }
  return (
    <Link
      href={`/app/subgroups/${encodeURIComponent(subgroupSlug)}`}
      aria-label={`Posted in ${name}`}
      onClick={(e) => e.stopPropagation()}
      className="rounded-full outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <Badge tone="accent">{name}</Badge>
    </Link>
  );
}

export default SourceBadge;
