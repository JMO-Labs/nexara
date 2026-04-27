'use client';
/**
 * @file components/chat/MessageList.tsx
 * @brief Virtualized message list. Loads older pages on scroll-to-top.
 *        Auto-scrolls to bottom on new live messages when already pinned.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import { AnimatePresence, motion } from 'framer-motion';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Skeleton, EmptyState } from '@/components/ui';
import type { ChatMessage } from '@/lib/api/chat';
import { MessageItem } from './MessageItem';

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

export function MessageList({
  messages,
  isLoading,
  hasMore,
  isFetchingMore,
  onLoadMore,
  selfId,
  onReply,
  onSendDm,
}: MessageListProps) {
  const parentRef = React.useRef<HTMLDivElement | null>(null);
  const pinnedToBottom = React.useRef(true);
  const prevCount = React.useRef(0);

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
      <AnimatePresence mode="wait">
        <motion.div
          key="sk"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        >
          <Stack spacing={1} p={2}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} height={48} />
            ))}
          </Stack>
        </motion.div>
      </AnimatePresence>
    );
  }

  if (ordered.length === 0) {
    return (
      <Box sx={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <EmptyState
          title="No messages yet"
          description="Send the first message to start the conversation."
        />
      </Box>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="ct"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
      >
        <Box
          ref={parentRef}
          onScroll={onScroll}
          sx={{ flex: 1, minHeight: 0, overflowY: 'auto', position: 'relative' }}
        >
      {isFetchingMore && (
        <Typography
          level="body-xs"
          textAlign="center"
          textColor="text.tertiary"
          sx={{ py: 1 }}
        >
          Loading older messages…
        </Typography>
      )}
      <Box
        sx={{
          height: virtualizer.getTotalSize(),
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((vi) => {
          const m = ordered[vi.index];
          if (!m) return null;
          const compact = isCompact(ordered[vi.index - 1], m);
          return (
            <Box
              key={vi.key}
              data-index={vi.index}
              ref={virtualizer.measureElement}
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${vi.start}px)`,
              }}
            >
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                <MessageItem
                  message={m}
                  compact={compact}
                  isSelf={Boolean(selfId && m.author?.id === selfId)}
                  onReply={onReply}
                  onSendDm={onSendDm}
                />
              </motion.div>
            </Box>
          );
        })}
      </Box>
        </Box>
      </motion.div>
    </AnimatePresence>
  );
}
