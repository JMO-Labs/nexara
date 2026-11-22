/**
 * @file components/members/GroupChips.tsx
 * @brief Small colored chips for shared groups.
 */
import { GroupDoor } from "@/components/ui/GroupDoor";
import type { SharedGroup } from "@/lib/api/users";
import { groupColor } from "@/lib/groupColor";

/**
 * @brief Row of group chips (max shown, "+N" overflow).
 * @param groups shared groups
 * @param max chips before collapsing into "+N"
 * @return chip row, or null when empty
 */
export function GroupChips({
  groups,
  max = 3,
}: {
  groups: SharedGroup[];
  max?: number;
}) {
  if (groups.length === 0) return null;
  const shown = groups.slice(0, max);
  const rest = groups.length - shown.length;
  return (
    <ul aria-label="Shared groups" className="flex flex-wrap gap-1.5">
      {shown.map((g) => (
        <li
          key={g.id}
          className="glass-item inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs text-ink"
        >
          <GroupDoor color={groupColor(g.id, g.accent_color)} />
          {g.name}
        </li>
      ))}
      {rest > 0 && (
        <li className="px-1 py-0.5 text-xs text-muted">+{rest} more</li>
      )}
    </ul>
  );
}
