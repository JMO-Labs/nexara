"use client";
/**
 * @file components/chat/ChatHead.tsx
 * @brief A single floating chat card (320x420). Shows header with peer/
 *        channel name, minimize/close controls, a MessageList, and Composer.
 *        Collapses to header bar when minimized.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { MinusIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { IconButton } from "@/components/ui";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import { useChatDock } from "@/stores/chatDock";
import {
  useMessages,
  useChatRealtime,
  sendChatMessage,
  sendChatTyping,
  optimisticAddMessage,
} from "@/hooks/useChat";
import { useSession } from "@/stores/session";
import type { ChatMessage } from "@/lib/api/chat";

export interface ChatHeadProps {
  threadId: string;
  label: string;
}

const CARD_W = 480;
const CARD_H = 560;
const HEADER_H = 44;

export function ChatHead({ threadId, label }: ChatHeadProps) {
  const prefersReduced = useReducedMotion();
  const closeThread = useChatDock((s) => s.closeThread);
  const toggleMinimize = useChatDock((s) => s.toggleMinimize);
  const isMinimized = useChatDock((s) => s.minimized[threadId] ?? false);
  const selfId = useSession((s) => s.user?.id ?? null);
  const qc = useQueryClient();
  const { markRead } = useChatRealtime();

  // Fix 2: capture focused element on mount; restore on unmount.
  const priorFocusRef = React.useRef<HTMLElement | null>(null);
  React.useEffect(() => {
    priorFocusRef.current =
      (document.activeElement as HTMLElement | null) ?? null;
    return () => {
      const prior = priorFocusRef.current;
      if (prior && document.contains(prior)) {
        prior.focus();
      } else {
        (
          document.getElementById("chat-launcher-pill") as HTMLElement | null
        )?.focus();
      }
    };
  }, []);

  const { data, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useMessages(threadId);

  const messages = React.useMemo<ChatMessage[]>(() => {
    if (!data) return [];
    return data.pages.flatMap((p) => p.items);
  }, [data]);

  const handleSend = (content: string) => {
    const optimistic: ChatMessage = {
      id: `optimistic-${Date.now()}`,
      channel_id: threadId,
      author: selfId
        ? { id: selfId, username: "", display_name: "", avatar_url: null }
        : null,
      content,
      edited_at: null,
      deleted: false,
      created_at: new Date().toISOString(),
    };
    optimisticAddMessage(qc, threadId, optimistic);
    sendChatMessage(threadId, content);
  };

  const handleTyping = () => sendChatTyping(threadId);

  const handleFocus = () => markRead(threadId);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.stopPropagation(); // Fix 2: prevent parent modal/dialog handling Escape
      closeThread(threadId);
    }
  };

  return (
    <Box
      role="region"
      aria-label={`Conversation with ${label}`}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      onFocus={handleFocus}
      sx={{
        width: CARD_W,
        height: isMinimized ? HEADER_H : CARD_H,
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.surface",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "md",
        boxShadow: "lg",
        overflow: "hidden",
        transition: "height 0.2s ease",
        "@media (prefers-reduced-motion: reduce)": { transition: "none" },
      }}
    >
      {/* Header */}
      <Stack
        direction="row"
        alignItems="center"
        sx={{
          px: 1.5,
          height: HEADER_H,
          flexShrink: 0,
          bgcolor: "background.level1",
          borderBottom: isMinimized ? "none" : "1px solid",
          borderColor: "divider",
          cursor: "pointer",
        }}
        onClick={() => isMinimized && toggleMinimize(threadId)}
      >
        <Typography level="title-sm" noWrap sx={{ flex: 1, minWidth: 0 }}>
          {label}
        </Typography>
        <IconButton
          size="sm"
          variant="plain"
          aria-label="Minimize"
          onClick={(e) => {
            e.stopPropagation();
            toggleMinimize(threadId);
          }}
        >
          <MinusIcon width={14} />
        </IconButton>
        <IconButton
          size="sm"
          variant="plain"
          aria-label="Close"
          onClick={(e) => {
            e.stopPropagation();
            closeThread(threadId);
          }}
        >
          <XMarkIcon width={14} />
        </IconButton>
      </Stack>

      {/* Body — hidden when minimized */}
      <AnimatePresence>
        {!isMinimized && (
          <motion.div
            key="body"
            initial={{ opacity: prefersReduced ? 1 : 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: prefersReduced ? 1 : 0 }}
            transition={{ duration: prefersReduced ? 0 : 0.15 }}
            style={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Box sx={{ flex: 1, minHeight: 0 }}>
              <MessageList
                messages={messages}
                isLoading={isLoading}
                hasMore={Boolean(hasNextPage)}
                isFetchingMore={isFetchingNextPage}
                onLoadMore={fetchNextPage}
                selfId={selfId}
              />
            </Box>
            <Composer onSend={handleSend} onTyping={handleTyping} />
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
}
