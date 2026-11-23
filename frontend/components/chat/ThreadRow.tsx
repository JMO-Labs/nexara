"use client";
/**
 * @file components/chat/ThreadRow.tsx
 * @brief Shared glass thread row: group dot/peer avatar, name, preview,
 *        unread/mention badge or time. Used by chat sidebar and Home tile.
 */
import { GroupDoor } from "@/components/ui/GroupDoor";
import * as React from "react";
import { Users, Trash2 } from "lucide-react";
import { IconButton } from "@/components/ui";
import { cn } from "@/lib/utils";

export interface ThreadRowProps {
  name: string;
  preview: string;
  /** Group colour (CSS colour) for the dot and tile tint. */
  color: string;
  /** Custom leading visual; defaults to initial (direct) or group icon. */
  avatar?: React.ReactNode;
  /** Show the first letter of name instead of the group icon. */
  initial?: boolean;
  unread?: number;
  mentions?: boolean;
  /** ISO timestamp shown when there is no badge. */
  time?: string | null;
  /** Relative time ("2h"), shown beside the unread badge. */
  timeLabel?: string | null;
  /** ~56px row (chat sidebar). */
  dense?: boolean;
  selected?: boolean;
  /** Home accordion state; sets aria-expanded. */
  expanded?: boolean;
  onClick: () => void;
  onDelete?: () => void;
  /** Extra classes on the main button (e.g. glass-item). */
  className?: string;
}

function clock(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

/**
 * @brief One thread row.
 * @param props see ThreadRowProps
 * @return row wrapper with main button and optional delete button
 */
export function ThreadRow({
  name,
  preview,
  color,
  avatar,
  initial,
  unread = 0,
  mentions,
  time,
  timeLabel,
  dense,
  selected,
  expanded,
  onClick,
  onDelete,
  className,
}: ThreadRowProps) {
  return (
    <div className="group relative">
      <button
        type="button"
        onClick={onClick}
        aria-expanded={expanded}
        aria-current={selected ? "true" : undefined}
        className={cn(
          "flex w-full items-center gap-3 rounded-[22px] text-left outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
          dense ? "p-2" : "p-3",
          selected &&
            "bg-[color-mix(in_srgb,var(--nx-ink)_8%,var(--nx-item))] shadow-[inset_0_0_0_1px_var(--nx-glass-hi)]",
          className,
        )}
      >
        {avatar ?? (
          <span
            aria-hidden
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full"
            style={{
              background: `color-mix(in srgb, ${color} 30%, transparent)`,
            }}
          >
            {initial ? (
              <span className="text-sm font-medium">{name.slice(0, 1)}</span>
            ) : (
              <Users className="h-5 w-5" />
            )}
          </span>
        )}
        <span className="min-w-0 flex-1">
          <strong className="flex items-center gap-1.5 font-medium">
            <GroupDoor color={color} />
            <span className="truncate">{name}</span>
          </strong>
          <small className="mt-0.5 block truncate text-[13px] text-[var(--nx-muted)]">
            {preview}
          </small>
        </span>
        {(() => {
          const badge = mentions ? (
            <span
              aria-label="Mentions you"
              className="grid h-[22px] min-w-[22px] place-items-center rounded-full bg-[var(--nx-red)] px-1.5 text-xs font-medium text-white"
            >
              @
            </span>
          ) : unread > 0 ? (
            <span
              aria-label={`${unread} unread`}
              className="grid h-[22px] min-w-[22px] place-items-center rounded-full bg-[var(--nx-blue)] px-1.5 text-xs font-medium text-white"
            >
              {unread}
            </span>
          ) : null;
          const stamp = timeLabel ? (
            <span className="text-xs text-[var(--nx-muted)]">{timeLabel}</span>
          ) : !badge && time ? (
            <time dateTime={time} className="text-xs text-[var(--nx-muted)]">
              {clock(time)}
            </time>
          ) : null;
          return badge || stamp ? (
            <span className="flex shrink-0 flex-col items-end gap-1">
              {stamp}
              {badge}
            </span>
          ) : null;
        })()}
      </button>
      {onDelete && (
        <IconButton
          aria-label="Delete conversation"
          size="sm"
          variant="ghost"
          className="absolute right-2 top-1/2 z-10 size-11 -translate-y-1/2 opacity-100 md:size-8 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
          onClick={onDelete}
        >
          <Trash2 className="size-4" aria-hidden="true" />
        </IconButton>
      )}
    </div>
  );
}
