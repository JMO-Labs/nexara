"use client";
/**
 * @file components/chat/MessageList.tsx
 * @brief Virtualized message list. Loads older pages on scroll-to-top.
 *        Auto-scrolls to bottom on new live messages when already pinned.
 */
import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { motion } from "framer-motion";
import { slideUp, fadeInOut, useMotionProps } from "@/components/ui/motion";
import { Skeleton, EmptyState } from "@/components/ui";
import type { ChatMessage } from "@/lib/api/chat";
import { MessageItem } from "./MessageItem";

export interface MessageListHandle {
  /** Force-scroll the viewport to the bottom on the next frame. */
  scrollToBottom: () => void;
}

export interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  hasMore: boolean;
  isFetchingMore: boolean;
  onLoadMore: () => void;
  selfId?: string | null;
  onReply?: (m: ChatMessage) => void;
  onSendDm?: (userId: string) => void;
}

const GROUP_GAP_MS = 5 * 60 * 1000;

function isCompact(prev: ChatMessage | undefined, cur: ChatMessage): boolean {
  if (!prev) return false;
  if (prev.author?.id !== cur.author?.id) return false;
  const a = new Date(prev.created_at).getTime();
  const b = new Date(cur.created_at).getTime();
  return Math.abs(b - a) < GROUP_GAP_MS;
}

export const MessageList = React.forwardRef<
  MessageListHandle,
  MessageListProps
>(function MessageList(
  {
    messages,
    isLoading,
    hasMore,
    isFetchingMore,
    onLoadMore,
    selfId,
    onReply,
    onSendDm,
  },
  forwardedRef,
) {
  const parentRef = React.useRef<HTMLDivElement | null>(null);
  const pinnedToBottom = React.useRef(true);
  const slide = useMotionProps(slideUp);
  const fade = useMotionProps(fadeInOut);
  const seen = React.useRef<Set<string> | null>(null);
  const prevCount = React.useRef(0);

  React.useImperativeHandle(
    forwardedRef,
    () => ({
      scrollToBottom: () => {
        pinnedToBottom.current = true;
        requestAnimationFrame(() => {
          const el = parentRef.current;
          if (el) el.scrollTop = el.scrollHeight;
        });
      },
    }),
    [],
  );

  // Render oldest -> newest. Backend returns newest-first, so reverse once.
  const ordered = React.useMemo(() => [...messages].reverse(), [messages]);

  const virtualizer = useVirtualizer({
    count: ordered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64,
    overscan: 8,
    getItemKey: (i) => ordered[i]?.id ?? i,
  });

  React.useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    if (prevCount.current === 0 || pinnedToBottom.current) {
      el.scrollTop = el.scrollHeight;
    }
    prevCount.current = ordered.length;
  }, [ordered.length]);

  React.useEffect(() => {
    seen.current = new Set(ordered.map((x) => x.id));
  });

  const onScroll = React.useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget;
      pinnedToBottom.current =
        el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      if (el.scrollTop < 60 && hasMore && !isFetchingMore) {
        onLoadMore();
      }
    },
    [hasMore, isFetchingMore, onLoadMore],
  );

  if (ordered.length === 0 && isLoading) {
    return (
      <motion.div
        data-testid="message-skeleton"
        className="flex min-h-0 flex-1 flex-col gap-2 p-4"
        {...fade}
      >
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} height={48} />
        ))}
      </motion.div>
    );
  }

  if (ordered.length === 0) {
    return (
      <div className="flex min-h-0 flex-1">
        <EmptyState
          title="No messages yet"
          description="Send the first message to start the conversation."
        />
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      onScroll={onScroll}
      className="relative min-h-0 flex-1 overflow-y-auto"
    >
      {isFetchingMore && (
        <p className="py-2 text-center text-xs text-muted">
          Loading older messages…
        </p>
      )}
      <div
        className="relative w-full"
        style={{ height: virtualizer.getTotalSize() }}
      >
        {virtualizer.getVirtualItems().map((vi) => {
          const m = ordered[vi.index];
          if (!m) return null;
          // Only messages arriving after first paint slide in.
          const isNew = seen.current !== null && !seen.current.has(m.id);
          return (
            <div
              key={vi.key}
              data-index={vi.index}
              ref={virtualizer.measureElement}
              className="absolute top-0 left-0 w-full"
              style={{ transform: `translateY(${vi.start}px)` }}
            >
              <motion.div {...(isNew ? slide : {})}>
                <MessageItem
                  message={m}
                  compact={isCompact(ordered[vi.index - 1], m)}
                  isSelf={Boolean(selfId && m.author?.id === selfId)}
                  onReply={onReply}
                  onSendDm={onSendDm}
                />
              </motion.div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
