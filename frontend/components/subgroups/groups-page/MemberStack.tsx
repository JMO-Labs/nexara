"use client";
/**
 * @file components/subgroups/groups-page/MemberStack.tsx
 * @brief Overlapping avatar stack of a group's members. Uses the list-provided
 *        preview when present; otherwise falls back to the lazy members query.
 */
import * as React from "react";
import { Avatar, AvatarGroup } from "@/components/ui/Avatar";
import { useSubgroupMembers } from "@/hooks/useSubgroups";
import type { MemberPreview } from "@/lib/api/subgroups";

export interface MemberStackProps {
  slug: string;
  /** Preview from the subgroup list response (no per-group request when set). */
  preview?: MemberPreview[];
  /** Total member count; drives the "+N" overflow badge. */
  count?: number;
}

/**
 * @brief Avatar stack for a group.
 * @param slug group slug (used only when preview is absent)
 * @param preview list-provided member preview
 * @param count total members, for the overflow badge
 * @return avatars, or null while loading / when empty
 */
export function MemberStack({ slug, preview, count }: MemberStackProps) {
  const fallback = useSubgroupMembers(preview === undefined ? slug : null);
  const people: MemberPreview[] =
    preview ??
    (fallback.data ?? []).map((m) => ({
      id: m.user_id,
      display_name: m.display_name ?? m.username ?? null,
      avatar_url: m.avatar_url ?? null,
    }));
  if (people.length === 0) return null;
  const extra = (count ?? people.length) - people.length;
  return (
    <div className="flex items-center">
      <AvatarGroup max={4}>
        {people.map((p) => (
          <Avatar
            key={p.id}
            size="md"
            src={p.avatar_url ?? undefined}
            name={p.display_name ?? undefined}
          />
        ))}
      </AvatarGroup>
      {extra > 0 && (
        <span className="ml-1 text-xs font-semibold text-ink">+{extra}</span>
      )}
    </div>
  );
}

export default MemberStack;
