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
import { ReportButton } from "@/components/common/ReportButton";
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
  /** Lowercase search text; matching spans are wrapped in <mark>. */
  highlight?: string;
}

/**
 * @brief Split text on a case-insensitive needle, wrapping hits in <mark>.
 * @param text message body
 * @param needle lowercase search text
 */
function marked(text: string, needle: string) {
  const lower = text.toLowerCase();
  const out: React.ReactNode[] = [];
  let i = 0;
  for (let at = lower.indexOf(needle); at >= 0; at = lower.indexOf(needle, i)) {
    if (at > i) out.push(text.slice(i, at));
    out.push(
      <mark key={at} className="rounded bg-accent/40 px-0.5 text-inherit">
        {text.slice(at, at + needle.length)}
      </mark>,
    );
    i = at + needle.length;
  }
  out.push(text.slice(i));
  return out;
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
  highlight = "",
}: MessageItemProps) {
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
      className={cn(
        "group relative flex items-start gap-3 px-4",
        density === "compact"
          ? compact
            ? "py-0"
            : "py-0.5"
          : compact
            ? "py-0.5"
            : "py-1.5",
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
            userId={message.author?.id}
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
              : "rounded-tl-sm bg-[var(--nx-bubble)]",
            deleted && "italic opacity-80",
          )}
        >
          {deleted ? (
            message.content
          ) : highlight ? (
            <p className="whitespace-pre-wrap break-words">
              {marked(message.content, highlight)}
            </p>
          ) : (
            <Markdown
              content={message.content}
              size="sm"
              mentions
              className={isSelf ? "text-inherit [&_a]:text-inherit" : undefined}
            />
          )}
        </div>
      </div>
      {!deleted && (
        <div className="hover-only flex items-center opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
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
          {!isSelf && !message.id.startsWith("optimistic-") && (
            <ReportButton
              targetType="message"
              targetId={message.id}
              className="rounded p-1 text-xs outline-none focus-visible:outline-2 focus-visible:outline-accent"
            />
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
