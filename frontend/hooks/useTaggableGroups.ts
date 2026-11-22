"use client";
/**
 * @file hooks/useTaggableGroups.ts
 * @brief Groups the viewer may @-tag, shaped as mention picker entries
 *        (username = slug). Mirrors the server rule in GroupTagService.
 */
import * as React from "react";
import { useSubgroupList } from "@/hooks/useSubgroups";
import type { Subgroup } from "@/lib/api/subgroups";
import type { UserSummary } from "@/lib/api/users";

export type MentionItem = UserSummary & { hint?: string };

/**
 * @brief Groups the viewer may @-tag, shaped as picker entries.
 * @param groups subgroup list
 * @return entries (username = slug)
 */
export function taggableGroups(groups: Subgroup[]): MentionItem[] {
  return groups
    .filter(
      (g) =>
        g.is_member &&
        !g.archived_at &&
        (g.tag_policy !== "admins" ||
          g.my_role === "owner" ||
          g.my_role === "moderator"),
    )
    .map((g) => ({
      id: `g:${g.id}`,
      username: g.slug,
      display_name: g.name,
      avatar_url: g.avatar_url,
      hint: "Group",
    }));
}

/** @brief Picker entries for groups the viewer may tag. */
export function useTaggableGroups(): MentionItem[] {
  const { data } = useSubgroupList();
  return React.useMemo(() => taggableGroups(data ?? []), [data]);
}
