"use client";
/**
 * @file components/subgroups/hub/GroupChatPanel.tsx
 * @brief Scoped, single-channel chat for a group hub. Renders message list +
 *        composer for the group's own channel only — no channel switcher, no
 *        DM list. Designed to live in a right-side drawer so the user can
 *        keep using the rest of the hub while chatting.
 */
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { IconButton, Skeleton } from "@/components/ui";
import { MessageList } from "@/components/chat/MessageList";
import { Composer } from "@/components/chat/Composer";
import {
  useSubgroupChannel,
  useMessages,
  useChatRealtime,
  optimisticAddMessage,
  sendChatMessage,
  sendChatTyping,
} from "@/hooks/useChat";
import { useSession } from "@/stores/session";
import type { ChatMessage } from "@/lib/api/chat";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface GroupChatPanelProps {
  subgroup: SubgroupDetail;
  onClose: () => void;
}

export function GroupChatPanel({ subgroup, onClose }: GroupChatPanelProps) {
  const qc = useQueryClient();
  const sessionUser = useSession((s) => s.user);
  const { data: channel, isLoading: channelLoading } = useSubgroupChannel(
    subgroup.id,
  );
  const channelId = channel?.id;
  const messagesQ = useMessages(channelId);
  const { typing, markRead } = useChatRealtime();
  const [replyTo, setReplyTo] = React.useState<ChatMessage | null>(null);

  React.useEffect(() => {
    if (channelId) markRead(channelId);
  }, [channelId, markRead]);

  const messages = React.useMemo(
    () => messagesQ.data?.pages.flatMap((p) => p.items) ?? [],
    [messagesQ.data],
  );

  const handleSend = React.useCallback(
    (raw: string) => {
      if (!channelId) return;
      let content = raw;
      if (replyTo) {
        const author = replyTo.author?.display_name ?? "someone";
        const excerpt = replyTo.content.slice(0, 140).replace(/\n/g, " ");
        content = `> @${author}: ${excerpt}\n\n${raw}`;
        setReplyTo(null);
      }

      if (sessionUser) {
        const optimistic: ChatMessage = {
          id: `optimistic-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          channel_id: channelId,
          author: {
            id: sessionUser.id,
            username: sessionUser.username,
            display_name: sessionUser.display_name,
            avatar_url: sessionUser.avatar_url,
          },
          content,
          edited_at: null,
          deleted: false,
          created_at: new Date().toISOString(),
        };
        optimisticAddMessage(qc, channelId, optimistic);
      }

      sendChatMessage(channelId, content);
    },
    [channelId, replyTo, sessionUser, qc],
  );

  const handleTyping = React.useCallback(() => {
    if (channelId) sendChatTyping(channelId);
  }, [channelId]);

  const typingCount = channelId ? (typing[channelId]?.length ?? 0) : 0;

  return (
    <div className="flex h-full min-h-0 flex-col border-l border-current/15 bg-bg">
      <div className="flex shrink-0 items-center justify-between border-b border-current/15 px-4 py-3">
        <div className="min-w-0">
          <p className="text-xs text-muted">Group chat</p>
          <h2 className="truncate text-base font-semibold">{subgroup.name}</h2>
        </div>
        <IconButton
          size="sm"
          variant="ghost"
          aria-label="Close chat"
          onClick={onClose}
        >
          <X className="size-4" aria-hidden />
        </IconButton>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {channelLoading || !channelId ? (
          <div className="p-4">
            <Skeleton height={300} />
          </div>
        ) : (
          <MessageList
            messages={messages}
            isLoading={messagesQ.isLoading}
            hasMore={!!messagesQ.hasNextPage}
            isFetchingMore={!!messagesQ.isFetchingNextPage}
            onLoadMore={() => messagesQ.fetchNextPage()}
            selfId={sessionUser?.id ?? null}
            onReply={(m) => setReplyTo(m)}
          />
        )}
      </div>

      {typingCount > 0 && (
        <p className="shrink-0 px-4 py-1 text-xs text-muted">
          {typingCount === 1
            ? "Someone is typing…"
            : `${typingCount} people typing…`}
        </p>
      )}

      <div className="shrink-0 border-t border-current/15">
        <Composer
          disabled={!channelId}
          onSend={handleSend}
          onTyping={handleTyping}
          placeholder={`Message #${subgroup.slug}`}
          replyTo={
            replyTo
              ? {
                  authorName: replyTo.author?.display_name ?? "someone",
                  excerpt: replyTo.content.slice(0, 100),
                }
              : null
          }
          onCancelReply={() => setReplyTo(null)}
        />
      </div>
    </div>
  );
}

export default GroupChatPanel;
