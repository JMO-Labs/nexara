'use client';
/**
 * @file components/chat/ChatLayout.tsx
 * @brief Two-pane chat shell: scrollable channel/DM list (left) + active
 *        thread (right, hidden when no selection on desktop). Composer
 *        is sticky at the bottom of the right pane and exposes media
 *        controls (emoji/media/poll). Toast on incoming messages for
 *        non-active channels.
 */
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { ArrowLeftIcon, PencilSquareIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { useQueryClient } from '@tanstack/react-query';
import { IconButton, EmptyState, Button } from '@/components/ui';
import { useToasts } from '@/stores/toasts';
import { useSession } from '@/stores/session';
import {
  useChannels,
  useDmThreads,
  useMessages,
  useChatRealtime,
  useCreateDm,
  useDeleteDm,
  optimisticAddMessage,
  sendChatMessage,
  sendChatTyping,
} from '@/hooks/useChat';
import { chatWs } from '@/lib/realtime/chat-ws';
import { ChannelList } from './ChannelList';
import { MessageList } from './MessageList';
import { Composer } from './Composer';
import { TypingIndicator } from './TypingIndicator';
import { NewDmModal } from './NewDmModal';
import type { ChatChannel, ChatMessage, DmThread } from '@/lib/api/chat';

export interface ChatLayoutProps {
  activeId: string | null;
}

function resolveTitle(
  channels: ChatChannel[],
  dms: DmThread[],
  id: string,
): string {
  const dm = dms.find((d) => d.channel_id === id);
  if (dm) return dm.peer.display_name;
  const ch = channels.find((c) => c.id === id);
  if (ch) return ch.channel_type === 'direct' ? ch.name : `# ${ch.name}`;
  return 'Conversation';
}

function statusLabel(status: string, fallback?: string): string | undefined {
  if (status === 'open') return undefined;
  if (status === 'connecting') return 'Connecting…';
  if (status === 'error') return 'Connection error — retrying.';
  if (status === 'closed') return fallback ?? 'Disconnected — reconnecting.';
  return undefined;
}

export function ChatLayout({ activeId }: ChatLayoutProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const sessionUser = useSession((s) => s.user);
  const channelsQ = useChannels();
  const dmsQ = useDmThreads();
  const messagesQ = useMessages(activeId ?? undefined);
  const { typing, unread, markRead, status } = useChatRealtime();
  const pushToast = useToasts((s) => s.push);
  const createDm = useCreateDm();
  const deleteDm = useDeleteDm();
  const [replyTo, setReplyTo] = React.useState<ChatMessage | null>(null);
  const [dmModalOpen, setDmModalOpen] = React.useState(false);
  const [threadPaneOpen, setThreadPaneOpen] = React.useState(false);

  // Drop reply context when switching channels (state-during-render pattern).
  const [prevChannel, setPrevChannel] = React.useState<string | null>(activeId);
  if (prevChannel !== activeId) {
    setPrevChannel(activeId);
    if (replyTo) setReplyTo(null);
  }

  const startDm = React.useCallback(
    async (userId: string) => {
      try {
        const channel = await createDm.mutateAsync(userId);
        router.push(`/app/chat/${channel.id}`);
      } catch (err) {
        pushToast({
          variant: 'danger',
          title: 'Could not open DM',
          message: err instanceof Error ? err.message : 'Try again later.',
          ttl: 5000,
        });
      }
    },
    [createDm, router, pushToast],
  );

  const handleSend = React.useCallback(
    (rawContent: string) => {
      if (!activeId) return;
      let content = rawContent;
      if (replyTo) {
        const author = replyTo.author?.display_name ?? 'someone';
        const excerpt = replyTo.content.slice(0, 140).replace(/\n/g, ' ');
        content = `> @${author}: ${excerpt}\n\n${rawContent}`;
        setReplyTo(null);
      }

      if (sessionUser) {
        const optimistic: ChatMessage = {
          id: `optimistic-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          channel_id: activeId,
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
        optimisticAddMessage(qc, activeId, optimistic);
      }

      sendChatMessage(activeId, content);
    },
    [activeId, replyTo, sessionUser, qc],
  );

  const channels = React.useMemo(
    () => channelsQ.data ?? [],
    [channelsQ.data],
  );
  const dms = React.useMemo(() => dmsQ.data ?? [], [dmsQ.data]);

  // Tell realtime hook which channel is active so unread doesn't bump.
  React.useEffect(() => {
    if (typeof window === 'undefined') return;
    const setter = (window as unknown as {
      __nx_chat_active?: (id: string | null) => void;
    }).__nx_chat_active;
    setter?.(activeId);
    if (activeId) markRead(activeId);
    return () => setter?.(null);
  }, [activeId, markRead]);

  // Toast on incoming chat.message frames for non-active channels.
  // Refresh channel + DM lists when an unknown channel surfaces (new DM
  // initiated by another user) so it appears live in the sidebar.
  React.useEffect(() => {
    return chatWs.subscribe((frame) => {
      if (frame.type !== 'chat.message') return;
      const msg = (frame.payload ?? {}) as unknown as ChatMessage;
      if (!msg?.channel_id) return;

      const isKnownDm = dms.some((d) => d.channel_id === msg.channel_id);
      const isKnownChannel = channels.some((c) => c.id === msg.channel_id);
      if (!isKnownDm && !isKnownChannel) {
        qc.invalidateQueries({ queryKey: ['chat', 'dms'] });
        qc.invalidateQueries({ queryKey: ['chat', 'channels'] });
      }

      if (msg.channel_id === activeId) return;
      const title =
        dms.find((d) => d.channel_id === msg.channel_id)?.peer.display_name ??
        channels.find((c) => c.id === msg.channel_id)?.name ??
        msg.author?.display_name ??
        'New message';
      pushToast({
        variant: 'info',
        title,
        message: msg.content.slice(0, 120),
        ttl: 5000,
      });
    });
  }, [activeId, channels, dms, pushToast, qc]);

  const select = (id: string) => router.push(`/app/chat/${id}`);
  const back = () => router.push('/app/chat');

  const messages = React.useMemo(
    () => messagesQ.data?.pages.flatMap((p) => p.items) ?? [],
    [messagesQ.data],
  );

  const typingCount = activeId ? (typing[activeId]?.length ?? 0) : 0;
  const showThread = Boolean(activeId);
  const connLabel = statusLabel(status);

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          md: threadPaneOpen ? '320px 1fr 320px' : '320px 1fr',
        },
        gridTemplateRows: '1fr',
        bgcolor: 'background.body',
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: {
            xs: showThread ? 'none' : 'flex',
            md: 'flex',
          },
          flexDirection: 'column',
          borderRight: { md: '1px solid' },
          borderColor: { md: 'divider' },
          minHeight: 0,
        }}
      >
        <Box
          sx={{
            p: 1,
            borderBottom: '1px solid',
            borderColor: 'divider',
            flexShrink: 0,
          }}
        >
          <Button
            size="sm"
            variant="soft"
            onClick={() => setDmModalOpen(true)}
            startDecorator={<PencilSquareIcon width={16} />}
            sx={{ width: '100%' }}
          >
            New direct message
          </Button>
        </Box>
        <Box sx={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          <ChannelList
            channels={channels}
            dms={dms}
            activeId={activeId}
            unread={unread}
            onSelect={select}
            onDeleteDm={async (channelId) => {
              if (
                typeof window !== 'undefined' &&
                !window.confirm('Remove this conversation from your inbox?')
              ) {
                return;
              }
              try {
                await deleteDm.mutateAsync(channelId);
                if (channelId === activeId) router.push('/app/chat');
                pushToast({
                  variant: 'success',
                  message: 'Conversation removed.',
                  ttl: 3000,
                });
              } catch (err) {
                pushToast({
                  variant: 'danger',
                  title: 'Could not delete',
                  message:
                    err instanceof Error ? err.message : 'Try again later.',
                  ttl: 5000,
                });
              }
            }}
            loading={channelsQ.isLoading || dmsQ.isLoading}
          />
        </Box>
      </Box>

      {showThread && activeId ? (
        <Stack
          sx={{
            minWidth: 0,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            sx={{
              px: 2,
              py: 1.25,
              borderBottom: '1px solid',
              borderColor: 'divider',
              bgcolor: 'background.surface',
            }}
          >
            <IconButton
              aria-label="Back to channel list"
              onClick={back}
              sx={{ display: { md: 'none' } }}
            >
              <ArrowLeftIcon width={18} />
            </IconButton>
            <Typography level="title-md" sx={{ flex: 1 }} noWrap>
              {resolveTitle(channels, dms, activeId)}
            </Typography>
            <IconButton
              aria-label={threadPaneOpen ? 'Close thread panel' : 'Open thread panel'}
              onClick={() => setThreadPaneOpen(!threadPaneOpen)}
              sx={{ display: { xs: 'none', md: 'flex' } }}
              tooltip={threadPaneOpen ? 'Close details' : 'Open details'}
            >
              <ChevronRightIcon width={18} />
            </IconButton>
          </Stack>

          <MessageList
            messages={messages}
            isLoading={messagesQ.isLoading}
            hasMore={messagesQ.hasNextPage ?? false}
            isFetchingMore={messagesQ.isFetchingNextPage}
            onLoadMore={() => messagesQ.fetchNextPage()}
            selfId={sessionUser?.id ?? null}
            onReply={setReplyTo}
            onSendDm={startDm}
          />

          <TypingIndicator count={typingCount} />

          <Composer
            disabled={status !== 'open'}
            connectionLabel={connLabel}
            onSend={handleSend}
            onTyping={() => sendChatTyping(activeId)}
            placeholder={
              status === 'open' ? 'Write a message…' : 'Connecting…'
            }
            replyTo={
              replyTo
                ? {
                    authorName: replyTo.author?.display_name ?? 'someone',
                    excerpt: replyTo.content.slice(0, 80),
                  }
                : null
            }
            onCancelReply={() => setReplyTo(null)}
          />
        </Stack>
      ) : (
        <Box
          sx={{
            display: { xs: 'none', md: 'flex' },
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <EmptyState
            title="Select a conversation"
            description="Choose a channel or direct message from the list to start chatting."
            action={<Button variant="solid" onClick={() => setDmModalOpen(true)}>Start conversation</Button>}
          />
        </Box>
      )}

      {/* Thread/Details Pane: 320px on desktop when open */}
      {threadPaneOpen && activeId && showThread && (
        <Box
          sx={{
            display: { xs: 'none', md: 'flex' },
            flexDirection: 'column',
            borderLeft: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.surface',
            minHeight: 0,
            minWidth: 0,
          }}
        >
          <Stack
            sx={{
              px: 2,
              py: 1.25,
              borderBottom: '1px solid',
              borderColor: 'divider',
              bgcolor: 'background.body',
              flexShrink: 0,
            }}
          >
            <Typography level="title-sm">Details</Typography>
          </Stack>
          <Stack
            sx={{
              flex: 1,
              overflow: 'auto',
              px: 2,
              py: 2,
              minHeight: 0,
            }}
          >
            <Typography level="body-sm" color="neutral">
              Thread details and conversation info will appear here.
            </Typography>
          </Stack>
        </Box>
      )}

      <NewDmModal
        open={dmModalOpen}
        onClose={() => setDmModalOpen(false)}
        onSelect={startDm}
        excludeUserId={sessionUser?.id ?? null}
      />
    </Box>
  );
}
