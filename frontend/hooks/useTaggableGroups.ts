"use client";
/**
 * @file hooks/useTaggableGroups.ts
 * @brief Extra @-mention picker entries beyond people: groups the viewer
 *        may tag (username = slug, mirrors GroupTagService) and household
 *        members/pets they can see (username = handle).
 */
import * as React from "react";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import type { HouseholdMember } from "@/lib/api/household";
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

/**
 * @brief Household members/pets with a handle, as picker entries.
 * @param members visible household members
 */
export function taggableHousehold(members: HouseholdMember[]): MentionItem[] {
  return members
    .filter((m) => m.handle)
    .map((m) => ({
      id: `h:${m.id}`,
      username: m.handle as string,
      display_name: m.name,
      avatar_url: null,
      hint: m.kind === "pet" ? (m.species ?? "Pet") : (m.relation ?? "Family"),
    }));
}

/** @brief Picker entries for groups and household members the viewer may tag. */
export function useTaggableGroups(): MentionItem[] {
  const { data } = useSubgroupList();
  const { data: household } = useVisibleHousehold();
  return React.useMemo(
    () => [
      ...taggableGroups(data ?? []),
      ...taggableHousehold(household ?? []),
    ],
    [data, household],
  );
}
