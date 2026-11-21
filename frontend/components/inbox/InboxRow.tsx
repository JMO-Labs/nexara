"use client";
/**
 * @file components/inbox/InboxRow.tsx
 * @brief Compact message-list row: glyph/avatar, title, one-line snippet,
 *        relative time and unread dot. Selected row takes the ink tint.
 */
import { formatDistanceToNowStrict } from "date-fns";
import { Avatar } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { InboxEntry } from "./useInboxItems";

/**
 * @brief One inbox list row.
 * @param entry normalised entry
 * @param selected row is open in the reading pane
 * @param onSelect open handler
 * @return row button
 */
export function InboxRow({
  entry,
  selected,
  onSelect,
}: {
  entry: InboxEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  const { Icon } = entry;
  let ago = "";
  try {
    ago = formatDistanceToNowStrict(new Date(entry.time), { addSuffix: false });
  } catch {
    ago = "";
  }
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected ? "true" : undefined}
      data-testid="inbox-row"
      data-unread={entry.unread || undefined}
      className={cn(
        "flex w-full items-start gap-3 rounded-[20px] px-3 py-2.5 text-left outline-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        selected
          ? "bg-surface-strong text-bg"
          : "text-ink hover:bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)]",
      )}
    >
      {entry.avatar ? (
        <Avatar
          size="sm"
          name={entry.avatar.name}
          src={entry.avatar.src ?? undefined}
        />
      ) : (
        <span
          aria-hidden="true"
          className={cn(
            "grid size-8 shrink-0 place-items-center rounded-full",
            selected ? "bg-bg/15" : "glass-item",
          )}
          style={entry.color ? { color: entry.color } : undefined}
        >
          {Icon ? (
            <Icon className="size-4" />
          ) : (
            <span className="size-2.5 rounded-full bg-current" />
          )}
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline gap-2">
          <span
            className={cn(
              "min-w-0 flex-1 truncate text-sm",
              entry.unread ? "font-semibold" : "font-medium",
            )}
          >
            {entry.title}
          </span>
          <span
            className={cn(
              "shrink-0 text-xs",
              selected ? "text-bg/70" : "text-muted",
            )}
          >
            {ago}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span
            className={cn(
              "min-w-0 flex-1 truncate text-xs",
              selected ? "text-bg/80" : "text-muted",
            )}
          >
            {entry.snippet}
          </span>
          {entry.unread && (
            <span
              aria-label="Unread"
              className="size-2 shrink-0 rounded-full bg-[var(--nx-blue)]"
            />
          )}
        </span>
      </span>
    </button>
  );
}
