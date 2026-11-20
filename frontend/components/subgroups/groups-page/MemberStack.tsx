"use client";
/**
 * @file components/subgroups/groups-page/MemberStack.tsx
 * @brief Overlapping avatar stack of a group's members (lazy, cached query).
 */
import * as React from "react";
import { Avatar, AvatarGroup } from "@/components/ui/Avatar";
import { useSubgroupMembers } from "@/hooks/useSubgroups";

/**
 * @brief Avatar stack for a group.
 * @param slug group slug
 * @return avatars, or null while loading / when empty
 */
export function MemberStack({ slug }: { slug: string }) {
  const { data } = useSubgroupMembers(slug);
  if (!data || data.length === 0) return null;
  return (
    <AvatarGroup max={4}>
      {data.map((m) => (
        <Avatar
          key={m.user_id}
          size="md"
          src={m.avatar_url ?? undefined}
          name={m.display_name ?? m.username ?? undefined}
        />
      ))}
    </AvatarGroup>
  );
}

export default MemberStack;
