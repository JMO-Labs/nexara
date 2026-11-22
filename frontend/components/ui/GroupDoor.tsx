/**
 * @file components/ui/GroupDoor.tsx
 * @brief A group's color as a small arched island door (round top, square
 *        foot). Decorative: the group name always sits beside it.
 */
import { cn } from "@/lib/utils";

const SIZES = {
  sm: "h-[11px] w-2",
  md: "h-3.5 w-2.5",
} as const;

/**
 * @brief Arched door swatch.
 * @param color CSS color (see groupColor)
 * @param size sm (pills, rows) or md (lists)
 * @return decorative span
 */
export function GroupDoor({
  color,
  size = "sm",
  className,
}: {
  color: string;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block shrink-0 rounded-t-full rounded-b-[2px]",
        SIZES[size],
        className,
      )}
      style={{ background: color }}
    />
  );
}
