"use client";
/**
 * @file components/chat/MessageItem.tsx
 * @brief Single chat message: avatar, author, time, bubble. Own bubbles use
 *        the strong surface; the leaf corner sits on the sender side.
 *        Hover/focus reveals Reply; other authors offer a Send DM action.
 */
import * as React from "react";
import { format } from "date-fns";
import { CornerUpLeft, MessageSquare } from "lucide-react";
import { Avatar, IconButton, Markdown } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/api/chat";

export interface MessageItemProps {
  message: ChatMessage;
  /** Compact mode hides avatar/name when grouping consecutive messages. */
  compact?: boolean;
  /** True when this message belongs to the active session user. */
  isSelf?: boolean;
  onReply?: (message: ChatMessage) => void;
  onSendDm?: (userId: string) => void;
  /** Spacing/font density. */
  density?: "comfortable" | "compact";
  /** Play the slide-up entrance (live messages only). */
  animate?: boolean;
  /** Called once the entrance finished or the row unmounted mid-way. */
  onAnimationDone?: (id: string) => void;
}

/**
 * @brief Chat message row.
 * @param props see MessageItemProps
 * @return message element
 */
export function MessageItem({
  message,
  compact,
  isSelf,
  onReply,
  onSendDm,
  density = "comfortable",
  animate,
  onAnimationDone,
}: MessageItemProps) {
  // Clear the "fresh" flag on unmount so a virtualized remount never replays.
  const id = message.id;
  React.useEffect(
    () => (animate ? () => onAnimationDone?.(id) : undefined),
    [animate, id, onAnimationDone],
  );

  let time = "";
  try {
    time = format(new Date(message.created_at), "p");
  } catch {
    time = "";
  }
  const name = message.author?.display_name ?? "Unknown";
  const authorId = message.author?.id;
  const deleted = message.deleted;

  return (
    <div
      data-density={density}
      data-message-id={message.id}
      onAnimationEnd={(e) => {
        if (e.target === e.currentTarget) onAnimationDone?.(message.id);
      }}
      className={cn(
        "group relative flex items-start gap-3 px-4",
        density === "compact"
          ? compact
            ? "py-0"
            : "py-0.5"
          : compact
            ? "py-0.5"
            : "py-1.5",
        animate && "nx-slide-up",
        isSelf && "flex-row-reverse",
        message.id.startsWith("optimistic-") && "opacity-60",
      )}
    >
      <div className="w-8 shrink-0">
        {!compact && (
          <Avatar
            size="md"
            name={name}
            src={message.author?.avatar_url ?? undefined}
          />
        )}
      </div>
      <div
        className={cn(
          "flex min-w-0 max-w-[85%] flex-col",
          isSelf && "items-end",
        )}
      >
        {!compact && (
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-semibold">{name}</span>
            <span className="text-xs text-muted">
              {time}
              {message.edited_at && " (edited)"}
            </span>
          </div>
        )}
        <div
          className={cn(
            "rounded-2xl px-3 text-sm",
            density === "compact" ? "py-1 text-xs" : "py-2",
            isSelf
              ? "rounded-tr-sm bg-surface-strong text-bg"
              : "rounded-tl-sm bg-surface",
            deleted && "italic opacity-80",
          )}
        >
          {deleted ? (
            message.content
          ) : (
            <Markdown content={message.content} size="sm" />
          )}
        </div>
      </div>
      {!deleted && (
        <div className="flex items-center opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          {onReply && (
            <IconButton
              aria-label="Reply"
              size="sm"
              variant="ghost"
              onClick={() => onReply(message)}
            >
              <CornerUpLeft size={14} aria-hidden />
            </IconButton>
          )}
          {onSendDm && authorId && !isSelf && (
            <IconButton
              aria-label={`Send DM to ${name}`}
              size="sm"
              variant="ghost"
              onClick={() => onSendDm(authorId)}
            >
              <MessageSquare size={14} aria-hidden />
            </IconButton>
          )}
        </div>
      )}
    </div>
  );
}
