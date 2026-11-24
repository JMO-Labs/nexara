/**
 * @file components/ui/BotBadge.tsx
 * @brief "Bot" pill shown beside plugin-bot names ("Bot (inactive)" when off).
 */
import { Badge } from "./Badge";

/**
 * @param active false when the plugin is disabled/uninstalled
 * @return badge
 */
export function BotBadge({ active = true }: { active?: boolean }) {
  return (
    <Badge tone="accent" className="px-2 py-0 text-[11px]">
      {active ? "Bot" : "Bot (inactive)"}
    </Badge>
  );
}

export default BotBadge;
