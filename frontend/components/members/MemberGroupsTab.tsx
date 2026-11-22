/**
 * @file components/members/MemberGroupsTab.tsx
 * @brief Groups shared between the viewer and a member.
 */
import { GroupDoor } from "@/components/ui/GroupDoor";
import { Users } from "lucide-react";
import { ListRow } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/EmptyState";
import type { SharedGroup } from "@/lib/api/users";
import { groupColor } from "@/lib/groupColor";

/**
 * @brief List of shared groups.
 * @param groups shared groups
 * @param name member display name for the empty copy
 * @return list or empty state
 */
export function MemberGroupsTab({
  groups,
  name,
}: {
  groups: SharedGroup[];
  name: string;
}) {
  if (groups.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title="No shared groups"
        description={`You and ${name} are not in any of the same groups yet.`}
      />
    );
  }
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {groups.map((g) => (
        <li key={g.id}>
          <ListRow>
            <span className="flex items-center gap-3 p-3 text-sm text-ink">
              <GroupDoor size="md" color={groupColor(g.id, g.accent_color)} />
              {g.name}
            </span>
          </ListRow>
        </li>
      ))}
    </ul>
  );
}
