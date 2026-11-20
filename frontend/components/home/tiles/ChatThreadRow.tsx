"use client";
/**
 * @file components/home/tiles/ChatThreadRow.tsx
 * @brief One chat thread row: group icon/dot, name, preview, badge.
 */
import * as React from "react";
import { Users } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { groupColor } from "@/lib/groupColor";
import type { HomeChatThread } from "@/lib/api/home";

export interface ChatThreadRowProps {
  thread: HomeChatThread;
  open: boolean;
  onOpen: () => void;
  children?: React.ReactNode;
}

function clock(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

/**
 * @brief Accordion row for a thread; renders children (the open thread) below.
 * @param props see ChatThreadRowProps
 * @return animated list item
 */
export function ChatThreadRow({
  thread,
  open,
  onOpen,
  children,
}: ChatThreadRowProps) {
  const reduce = useReducedMotion();
  const color = groupColor(thread.subgroup_id, null);
  const preview = thread.last_message
    ? `${thread.last_message.author_name ? `${thread.last_message.author_name}: ` : ""}${thread.last_message.content}`
    : "No messages yet";
  return (
    <motion.li
      layout={reduce ? false : "position"}
      className={cn(
        "flex list-none flex-col rounded-[22px]",
        open && "glass-item min-h-0 flex-1",
      )}
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={onOpen}
        className={cn(
          "flex w-full items-center gap-3 rounded-[22px] p-3 text-left",
          !open && "motion-safe:[@media(hover:hover)]:hover:bg-white/25",
        )}
      >
        <span
          aria-hidden
          className="grid h-10 w-10 shrink-0 place-items-center rounded-[14px]"
          style={{
            background: `color-mix(in srgb, ${color} 30%, transparent)`,
          }}
        >
          {thread.channel_type === "direct" && thread.peer ? (
            <span className="text-sm font-medium">
              {thread.peer.display_name.slice(0, 1)}
            </span>
          ) : (
            <Users className="h-5 w-5" />
          )}
        </span>
        <span className="min-w-0 flex-1">
          <strong className="flex items-center gap-1.5 font-medium">
            <i
              aria-hidden
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: color }}
            />
            <span className="truncate">{thread.name}</span>
          </strong>
          <small className="mt-0.5 block truncate text-[13px] text-[var(--nx-muted)]">
            {preview}
          </small>
        </span>
        {thread.mentions_me ? (
          <span
            aria-label="Mentions you"
            className="grid h-[22px] min-w-[22px] place-items-center rounded-full bg-[var(--nx-red)] px-1.5 text-xs font-medium text-white"
          >
            @
          </span>
        ) : thread.unread_count > 0 ? (
          <span
            aria-label={`${thread.unread_count} unread`}
            className="grid h-[22px] min-w-[22px] place-items-center rounded-full bg-[var(--nx-blue)] px-1.5 text-xs font-medium text-white"
          >
            {thread.unread_count}
          </span>
        ) : thread.last_message ? (
          <time
            dateTime={thread.last_message.created_at}
            className="text-xs text-[var(--nx-muted)]"
          >
            {clock(thread.last_message.created_at)}
          </time>
        ) : null}
      </button>
      {children}
    </motion.li>
  );
}
