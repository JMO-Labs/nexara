"use client";
/**
 * @file components/mentions/MentionMenu.tsx
 * @brief Suggestion list for @mentions and tag pickers (keyboard handled by
 *        the owning input via ``active``).
 */
import type * as React from "react";
import { Avatar } from "@/components/ui/Avatar";
import type { UserSummary } from "@/lib/api/users";
import { cn } from "@/lib/utils";

/**
 * @brief Member suggestions.
 * @param items matches
 * @param active highlighted index
 * @param onPick choose a member
 * @param id listbox id (for aria-controls)
 * @return listbox or null when empty
 */
export function MentionMenu({
  items,
  active,
  onPick,
  id,
  className,
  style,
}: {
  items: (UserSummary & { hint?: string })[];
  active: number;
  onPick: (u: UserSummary & { hint?: string }) => void;
  id?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  if (items.length === 0) return null;
  return (
    <ul
      id={id}
      role="listbox"
      aria-label="People"
      style={style}
      className={cn(
        "z-50 w-64 overflow-hidden rounded-[20px] border border-[var(--nx-line)] bg-[var(--nx-glass-solid)] p-1.5 shadow-[0_18px_40px_-16px_rgba(0,0,0,0.5)]",
        className,
      )}
    >
      {items.map((u, i) => (
        <li
          key={u.id}
          role="option"
          aria-selected={i === active}
          onMouseDown={(e) => {
            e.preventDefault(); // keep focus in the input
            onPick(u);
          }}
          className={cn(
            "flex cursor-pointer items-center gap-2.5 rounded-full px-2 py-1.5 text-sm",
            i === active
              ? "bg-surface-strong text-bg"
              : "hover:bg-[color-mix(in_srgb,var(--nx-ink)_7%,transparent)]",
          )}
        >
          <Avatar
            size="sm"
            name={u.display_name}
            src={u.avatar_url ?? undefined}
          />
          <span className="min-w-0 flex-1 truncate">{u.display_name}</span>
          <span
            className={cn(
              "text-xs",
              i === active ? "text-bg/70" : "text-muted",
            )}
          >
            {u.hint ?? `@${u.username}`}
          </span>
        </li>
      ))}
    </ul>
  );
}
