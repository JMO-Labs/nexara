"use client";
/**
 * @file components/chat/MessageList.tsx
 * @brief Virtualized message list. Loads older pages on scroll-to-top.
 *        Auto-scrolls to bottom on new live messages when already pinned.
 */
import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Skeleton, EmptyState, Button } from "@/components/ui";
import type { ChatMessage } from "@/lib/api/chat";
import { MessageItem } from "./MessageItem";
import { dayLabel, isGrouped, startsNewDay } from "./grouping";

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
  /** Fetch failed: show retry state. */
  isError?: boolean;
  onRetry?: () => void;
  /** CTA in the empty state (e.g. focus the composer). */
  onStartConversation?: () => void;
  /** Row density. */
  density?: "comfortable" | "compact";
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
    isError,
    onRetry,
    onStartConversation,
    density = "comfortable",
  },
  forwardedRef,
) {
  const parentRef = React.useRef<HTMLDivElement | null>(null);
  const pinnedToBottom = React.useRef(true);
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

  // Ids present at first render don't animate; later arrivals slide up.
  const seen = React.useRef<Set<string> | null>(null);
  const fresh = React.useRef<Set<string>>(new Set());
  if (seen.current === null) {
    seen.current = new Set(ordered.map((m) => m.id));
  } else {
    for (const m of ordered) {
      if (!seen.current.has(m.id)) {
        seen.current.add(m.id);
        fresh.current.add(m.id);
      }
    }
  }

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

  if (ordered.length === 0 && isError) {
    return (
      <div className="flex min-h-0 flex-1" role="alert">
        <EmptyState
          title="Couldn't load messages"
          description="Check your connection and try again."
          action={<Button onClick={onRetry}>Retry</Button>}
        />
      </div>
    );
  }

  if (ordered.length === 0 && isLoading) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2 p-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} height={48} />
        ))}
      </div>
    );
  }

  if (ordered.length === 0) {
    return (
      <div className="flex min-h-0 flex-1">
        <EmptyState
          title="No messages yet"
          description="Send the first message to start the conversation."
          action={
            onStartConversation && (
              <Button onClick={onStartConversation}>Start conversation</Button>
            )
          }
        />
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      onScroll={onScroll}
      data-density={density}
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
          return (
            <div
              key={vi.key}
              data-index={vi.index}
              ref={virtualizer.measureElement}
              className="absolute top-0 left-0 w-full"
              style={{ transform: `translateY(${vi.start}px)` }}
            >
              {startsNewDay(ordered[vi.index - 1], m) && (
                <div
                  role="separator"
                  aria-label={dayLabel(m.created_at)}
                  className="px-4 py-2 text-center text-xs font-medium text-muted"
                >
                  {dayLabel(m.created_at)}
                </div>
              )}
              <MessageItem
                message={m}
                compact={isGrouped(ordered[vi.index - 1], m)}
                isSelf={Boolean(selfId && m.author?.id === selfId)}
                onReply={onReply}
                onSendDm={onSendDm}
                density={density}
                animate={fresh.current.has(m.id)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
});
