"use client";
/**
 * @file components/chat/ChatLayout.tsx
 * @brief Chat shell. Desktop: channel list (280px) + conversation (+ details).
 *        Phone: list at /app/chat, conversation at /app/chat/[id]. Toasts on
 *        incoming messages for non-active channels.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { EmptyState, Button } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import { useSession } from "@/stores/session";
import { useUI } from "@/stores/ui";
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
} from "@/hooks/useChat";
import { chatWs } from "@/lib/realtime/chat-ws";
import { NewDmModal } from "./NewDmModal";
import { SidebarPane } from "./chat-layout/SidebarPane";
import { ThreadPane, DetailsPane } from "./chat-layout/ThreadPane";
import {
  gridClass,
  isDesktop,
  pickDefaultChannel,
  readLastChannel,
  resolveTitle,
  statusLabel,
  writeLastChannel,
} from "./chat-layout/helpers";
import { useConfirmDialog } from "@/stores/confirmDialog";
import type { ChatMessage } from "@/lib/api/chat";

export interface ChatLayoutProps {
  activeId: string | null;
}

/**
 * @brief Two-pane chat shell.
 * @param activeId selected channel/DM id or null
 * @return layout element
 */
export function ChatLayout({ activeId }: ChatLayoutProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const sessionUser = useSession((s) => s.user);
  const channelsQ = useChannels();
  const dmsQ = useDmThreads();
  const messagesQ = useMessages(activeId ?? undefined);
  const { typing, unread, markRead, status } = useChatRealtime();
  const pushToast = useToasts((s) => s.push);
  const chatToastsMuted = useUI((s) => s.chatToastsMuted);
  const toggleChatToastsMuted = useUI((s) => s.toggleChatToastsMuted);
  const createDm = useCreateDm();
  const deleteDm = useDeleteDm();
  const confirm = useConfirmDialog((s) => s.confirm);
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
          variant: "danger",
          title: "Could not open DM",
          message: err instanceof Error ? err.message : "Try again later.",
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
        const author = replyTo.author?.display_name ?? "someone";
        const excerpt = replyTo.content.slice(0, 140).replace(/\n/g, " ");
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
      writeLastChannel(activeId);
    },
    [activeId, replyTo, sessionUser, qc],
  );

  const channels = React.useMemo(() => channelsQ.data ?? [], [channelsQ.data]);
  const dms = React.useMemo(() => dmsQ.data ?? [], [dmsQ.data]);

  // Auto-select last-used channel (or community default) on bare /app/chat.
  const channelsLoaded = !channelsQ.isLoading;
  const dmsLoaded = !dmsQ.isLoading;
  React.useEffect(() => {
    if (activeId) return;
    if (!channelsLoaded || !dmsLoaded) return;
    const target = pickDefaultChannel(channels, dms, readLastChannel());
    if (target && isDesktop()) router.replace(`/app/chat/${target}`);
  }, [activeId, channelsLoaded, dmsLoaded, channels, dms, router]);

  // Tell realtime hook which channel is active so unread doesn't bump.
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const setter = (
      window as unknown as {
        __nx_chat_active?: (id: string | null) => void;
      }
    ).__nx_chat_active;
    setter?.(activeId);
    if (activeId) markRead(activeId);
    return () => setter?.(null);
  }, [activeId, markRead]);

  // Toast on incoming chat.message frames for non-active channels.
  // Refresh channel + DM lists when an unknown channel surfaces (new DM
  // initiated by another user) so it appears live in the sidebar.
  React.useEffect(() => {
    return chatWs.subscribe((frame) => {
      if (frame.type !== "chat.message") return;
      const msg = (frame.payload ?? {}) as unknown as ChatMessage;
      if (!msg?.channel_id) return;

      const isKnownDm = dms.some((d) => d.channel_id === msg.channel_id);
      const isKnownChannel = channels.some((c) => c.id === msg.channel_id);
      if (!isKnownDm && !isKnownChannel) {
        qc.invalidateQueries({ queryKey: ["chat", "dms"] });
        qc.invalidateQueries({ queryKey: ["chat", "channels"] });
      }

      if (msg.channel_id === activeId) {
        writeLastChannel(activeId);
        return;
      }
      if (chatToastsMuted) return;
      const title =
        dms.find((d) => d.channel_id === msg.channel_id)?.peer.display_name ??
        channels.find((c) => c.id === msg.channel_id)?.name ??
        msg.author?.display_name ??
        "New message";
      pushToast({
        variant: "info",
        title,
        message: msg.content.slice(0, 120),
        ttl: 5000,
      });
    });
  }, [activeId, channels, dms, pushToast, qc, chatToastsMuted]);

  const select = (id: string) => router.push(`/app/chat/${id}`);
  const back = () => router.push("/app/chat");

  const messages = React.useMemo(
    () => messagesQ.data?.pages.flatMap((p) => p.items) ?? [],
    [messagesQ.data],
  );

  const typingCount = activeId ? (typing[activeId]?.length ?? 0) : 0;

  const onDeleteDm = async (channelId: string) => {
    const ok = await confirm({
      title: "Remove conversation?",
      message: "This conversation will be removed from your inbox.",
      confirmLabel: "Remove",
      tone: "neutral",
    });
    if (!ok) return;
    try {
      await deleteDm.mutateAsync(channelId);
      if (channelId === activeId) router.push("/app/chat");
      pushToast({
        variant: "success",
        message: "Conversation removed.",
        ttl: 3000,
      });
    } catch (err) {
      pushToast({
        variant: "danger",
        title: "Could not delete",
        message: err instanceof Error ? err.message : "Try again later.",
        ttl: 5000,
      });
    }
  };

  const showDetails = threadPaneOpen && Boolean(activeId);

  return (
    <div className={gridClass(showDetails)}>
      <SidebarPane
        className={activeId ? "hidden md:flex" : "flex"}
        channels={channels}
        dms={dms}
        activeId={activeId}
        unread={unread}
        onSelect={select}
        onDeleteDm={onDeleteDm}
        loading={channelsQ.isLoading || dmsQ.isLoading}
        muted={chatToastsMuted}
        onToggleMute={toggleChatToastsMuted}
        onNewDm={() => setDmModalOpen(true)}
      />

      {activeId ? (
        <ThreadPane
          key={activeId}
          title={resolveTitle(channels, dms, activeId)}
          onBack={back}
          detailsOpen={threadPaneOpen}
          onToggleDetails={() => setThreadPaneOpen((o) => !o)}
          list={{
            messages,
            isLoading: messagesQ.isLoading,
            isError: messagesQ.isError,
            onRetry: () => void messagesQ.refetch(),
            hasMore: messagesQ.hasNextPage ?? false,
            isFetchingMore: messagesQ.isFetchingNextPage,
            onLoadMore: () => messagesQ.fetchNextPage(),
            selfId: sessionUser?.id ?? null,
            onReply: setReplyTo,
            onSendDm: startDm,
          }}
          typingCount={typingCount}
          composer={{
            disabled: status !== "open",
            connectionLabel: statusLabel(status),
            onSend: handleSend,
            onTyping: () => sendChatTyping(activeId),
            placeholder: status === "open" ? "Write a message…" : "Connecting…",
            replyTo: replyTo
              ? {
                  authorName: replyTo.author?.display_name ?? "someone",
                  excerpt: replyTo.content.slice(0, 80),
                }
              : null,
            onCancelReply: () => setReplyTo(null),
          }}
        />
      ) : (
        <div className="hidden items-center justify-center md:flex">
          <EmptyState
            title="Select a conversation"
            description="Choose a channel or direct message from the list to start chatting."
            action={
              <Button onClick={() => setDmModalOpen(true)}>
                Start conversation
              </Button>
            }
          />
        </div>
      )}

      {showDetails && <DetailsPane />}

      <NewDmModal
        open={dmModalOpen}
        onClose={() => setDmModalOpen(false)}
        onSelect={startDm}
        excludeUserId={sessionUser?.id ?? null}
      />
    </div>
  );
}
