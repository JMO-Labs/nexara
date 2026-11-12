"use client";
/**
 * @file components/chat/ChatHead.tsx
 * @brief A single floating chat card (320x420). Shows header with peer/
 *        channel name, minimize/close controls, a MessageList, and Composer.
 *        Collapses to header bar when minimized.
 */
import * as React from "react";
import { Minus, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { IconButton } from "@/components/ui";
import { MessageList, type MessageListHandle } from "./MessageList";
import { Composer, type ComposerHandle } from "./Composer";
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

  const {
    data,
    isLoading,
    isError,
    refetch,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useMessages(threadId);

  const messages = React.useMemo<ChatMessage[]>(() => {
    if (!data) return [];
    return data.pages.flatMap((p) => p.items);
  }, [data]);

  const composerRef = React.useRef<ComposerHandle | null>(null);
  const listRef = React.useRef<MessageListHandle | null>(null);

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
    listRef.current?.scrollToBottom();
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
    <div
      role="region"
      aria-label={`Conversation with ${label}`}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      onFocus={handleFocus}
      style={{ width: CARD_W, height: isMinimized ? HEADER_H : CARD_H }}
      className="flex max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-border bg-bg text-ink shadow-lg motion-safe:transition-[height] motion-safe:duration-200"
    >
      <div
        style={{ height: HEADER_H }}
        className={`flex shrink-0 items-center gap-1 bg-surface px-3 ${
          isMinimized ? "cursor-pointer" : "border-b border-border"
        }`}
        onClick={() => isMinimized && toggleMinimize(threadId)}
      >
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold">
          {label}
        </h2>
        <IconButton
          size="sm"
          variant="ghost"
          aria-label="Minimize"
          onClick={(e) => {
            e.stopPropagation();
            toggleMinimize(threadId);
          }}
        >
          <Minus size={14} aria-hidden />
        </IconButton>
        <IconButton
          size="sm"
          variant="ghost"
          aria-label="Close"
          onClick={(e) => {
            e.stopPropagation();
            closeThread(threadId);
          }}
        >
          <X size={14} aria-hidden />
        </IconButton>
      </div>

      {/* min-h-0 lets MessageList scroll without overlapping the Composer. */}
      {!isMinimized && (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-1 flex-col">
            <MessageList
              ref={listRef}
              messages={messages}
              isLoading={isLoading}
              isError={isError}
              onRetry={() => void refetch()}
              hasMore={Boolean(hasNextPage)}
              isFetchingMore={isFetchingNextPage}
              onLoadMore={fetchNextPage}
              selfId={selfId}
              onStartConversation={() => composerRef.current?.focus()}
            />
          </div>
          <div className="shrink-0 border-t border-border">
            <Composer
              ref={composerRef}
              onSend={handleSend}
              onTyping={handleTyping}
            />
          </div>
        </div>
      )}
    </div>
  );
}
