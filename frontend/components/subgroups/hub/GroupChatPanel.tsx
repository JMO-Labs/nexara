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
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { XMarkIcon } from "@heroicons/react/24/outline";
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
    <Stack
      sx={{
        height: "100%",
        minHeight: 0,
        bgcolor: "background.body",
        borderLeft: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: "1px solid",
          borderColor: "divider",
          flexShrink: 0,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography
            level="title-sm"
            sx={{
              fontFamily: "var(--font-display)",
              textTransform: "uppercase",
              letterSpacing: "0.14em",
              color: "text.tertiary",
              fontSize: "10px",
            }}
          >
            Group chat
          </Typography>
          <Typography level="title-md" noWrap>
            {subgroup.name}
          </Typography>
        </Box>
        <IconButton
          size="sm"
          variant="plain"
          color="neutral"
          aria-label="Close chat"
          onClick={onClose}
        >
          <XMarkIcon style={{ width: 18, height: 18 }} />
        </IconButton>
      </Stack>

      <Box
        sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}
      >
        {channelLoading || !channelId ? (
          <Box sx={{ p: 2 }}>
            <Skeleton height={300} />
          </Box>
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
      </Box>

      {typingCount > 0 && (
        <Typography
          level="body-xs"
          sx={{ px: 2, py: 0.5, color: "text.tertiary", flexShrink: 0 }}
        >
          {typingCount === 1
            ? "Someone is typing…"
            : `${typingCount} people typing…`}
        </Typography>
      )}

      <Box
        sx={{ flexShrink: 0, borderTop: "1px solid", borderColor: "divider" }}
      >
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
      </Box>
    </Stack>
  );
}

export default GroupChatPanel;
