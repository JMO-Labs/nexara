"use client";
/**
 * @file components/home/tiles/ChatThreadRow.tsx
 * @brief Home accordion wrapper around the shared chat ThreadRow.
 */
import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { groupColor } from "@/lib/groupColor";
import { ThreadRow } from "@/components/chat/ThreadRow";
import type { HomeChatThread } from "@/lib/api/home";

export interface ChatThreadRowProps {
  thread: HomeChatThread;
  open: boolean;
  onOpen: () => void;
  children?: React.ReactNode;
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
  const last = thread.last_message;
  const preview = last
    ? `${last.author_name ? `${last.author_name}: ` : ""}${last.content}`
    : "No messages yet";
  return (
    <motion.li
      layout={reduce ? false : "position"}
      className={cn(
        "flex list-none flex-col rounded-[22px]",
        open && "glass-item",
      )}
    >
      <ThreadRow
        name={thread.name}
        preview={preview}
        color={groupColor(thread.subgroup_id, null)}
        initial={thread.channel_type === "direct" && !!thread.peer}
        unread={thread.unread_count}
        mentions={thread.mentions_me}
        time={last?.created_at}
        expanded={open}
        onClick={onOpen}
        className={
          !open
            ? "motion-safe:[@media(hover:hover)]:hover:bg-white/25"
            : undefined
        }
      />
      {children}
    </motion.li>
  );
}
