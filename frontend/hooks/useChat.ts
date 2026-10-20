"use client";
/**
 * @file hooks/useChat.ts
 * @brief TanStack Query hooks + WS bridge for chat. Channels list, message
 *        history (infinite), DM threads, send/typing helpers, and a realtime
 *        hook that pushes incoming chat.* frames into the React Query cache.
 */
import * as React from "react";
import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import {
  type ChatMessage,
  type MessageHistoryPage,
  createOrGetDm,
  deleteDmThread,
  ensureSubgroupChannel,
  getMessageHistory,
  listChannels,
  listDmThreads,
} from "@/lib/api/chat";
import { chatWs, type WsFrame, type WsStatus } from "@/lib/realtime/chat-ws";

type InfiniteHistory = {
  pages: MessageHistoryPage[];
  pageParams: (string | null)[];
};

export function useChannels() {
  return useQuery({
    queryKey: qk.chat.channels(),
    queryFn: listChannels,
    staleTime: 60_000,
  });
}

export function useDmThreads() {
  return useQuery({
    queryKey: qk.chat.dms(),
    queryFn: listDmThreads,
    staleTime: 60_000,
  });
}

export function useMessages(channelId: string | undefined, limit = 50) {
  return useInfiniteQuery({
    queryKey: qk.chat.messages(channelId ?? ""),
    queryFn: ({ pageParam }) =>
      getMessageHistory(channelId!, pageParam as string | null, limit),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.cursor : undefined),
    enabled: Boolean(channelId),
    staleTime: 15_000,
  });
}

export function useCreateDm() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (peerId: string) => createOrGetDm(peerId),
    successKey: "toasts.subgroups.member.added",
    silentSuccess: true,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.chat.dms() });
      qc.invalidateQueries({ queryKey: qk.chat.channels() });
    },
  });
}

export function useDeleteDm() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (channelId: string) => deleteDmThread(channelId),
    onSuccess: (_void, channelId) => {
      qc.removeQueries({ queryKey: qk.chat.messages(channelId) });
      qc.invalidateQueries({ queryKey: qk.chat.dms() });
      qc.invalidateQueries({ queryKey: qk.chat.channels() });
    },
  });
}

export function useEnsureSubgroupChannel() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (subgroupId: string) => ensureSubgroupChannel(subgroupId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.chat.channels() }),
  });
}

/**
 * @brief Fetch or create a subgroup's channel via query (auto-fetches on mount).
 */
export function useSubgroupChannel(subgroupId: string) {
  return useQuery({
    queryKey: qk.chat.subgroupChannel(subgroupId),
    queryFn: () => ensureSubgroupChannel(subgroupId),
    staleTime: Infinity,
  });
}

/**
 * @brief Acquire the singleton chat WS, expose status and a `send` helper.
 *        Ref-counted across components; the socket auto-disconnects when
 *        no consumers remain.
 */
export function useChatWs(): { status: WsStatus; send: typeof chatWs.send } {
  const [status, setStatus] = React.useState<WsStatus>("closed");

  React.useEffect(() => {
    chatWs.acquire();
    const off = chatWs.onStatus(setStatus);
    return () => {
      off();
      chatWs.release();
    };
  }, []);

  return { status, send: chatWs.send.bind(chatWs) };
}

function prependMessage(
  data: InfiniteHistory | undefined,
  msg: ChatMessage,
): InfiniteHistory | undefined {
  if (!data || data.pages.length === 0) {
    return {
      pages: [{ items: [msg], cursor: null, has_more: false }],
      pageParams: [null],
    };
  }
  const [first, ...rest] = data.pages;
  if (first.items.some((m) => m.id === msg.id)) return data;

  // Replace any optimistic placeholder with the same content from the same
  // author within the last 10 seconds.
  const cutoff = Date.now() - 10_000;
  const idx = first.items.findIndex(
    (m) =>
      m.id.startsWith("optimistic-") &&
      m.content === msg.content &&
      m.author?.id === msg.author?.id &&
      new Date(m.created_at).getTime() > cutoff,
  );
  if (idx !== -1) {
    const items = [...first.items];
    items[idx] = msg;
    return { ...data, pages: [{ ...first, items }, ...rest] };
  }

  return {
    ...data,
    pages: [{ ...first, items: [msg, ...first.items] }, ...rest],
  };
}

/**
 * @brief Imperative helper to write an optimistic local message into the
 *        chat history cache before the WS broadcast round-trips.
 */
export function optimisticAddMessage(
  qc: ReturnType<typeof useQueryClient>,
  channelId: string,
  msg: ChatMessage,
): void {
  qc.setQueryData<InfiniteHistory | undefined>(
    qk.chat.messages(channelId),
    (old) => prependMessage(old, msg),
  );
}

function patchMessage(
  data: InfiniteHistory | undefined,
  patch: ChatMessage,
): InfiniteHistory | undefined {
  if (!data) return data;
  return {
    ...data,
    pages: data.pages.map((p) => ({
      ...p,
      items: p.items.map((m) => (m.id === patch.id ? { ...m, ...patch } : m)),
    })),
  };
}

interface TypingState {
  channelId: string;
  userId: string;
  at: number;
}

/**
 * @brief Subscribe to chat.* frames and reflect them in the React Query cache.
 *        Also exposes the live "who is typing" set per channel.
 */
export function useChatRealtime(): {
  status: WsStatus;
  typing: Record<string, string[]>;
  send: typeof chatWs.send;
  unread: Record<string, number>;
  markRead: (channelId: string) => void;
} {
  const qc = useQueryClient();
  const { status, send } = useChatWs();
  const [typing, setTyping] = React.useState<Record<string, TypingState[]>>({});
  const [unread, setUnread] = React.useState<Record<string, number>>({});
  const activeChannel = React.useRef<string | null>(null);

  // Expose channel-set helper via ref to keep effect deps stable.
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      (
        window as unknown as { __nx_chat_active?: (id: string | null) => void }
      ).__nx_chat_active = (id) => {
        activeChannel.current = id;
      };
    }
  }, []);

  React.useEffect(() => {
    return chatWs.subscribe((frame: WsFrame) => {
      const payload = (frame.payload ?? {}) as Record<string, unknown>;
      switch (frame.type) {
        case "chat.message": {
          const msg = payload as unknown as ChatMessage;
          if (!msg?.channel_id) return;
          qc.setQueryData<InfiniteHistory | undefined>(
            qk.chat.messages(msg.channel_id),
            (old) => prependMessage(old, msg),
          );
          if (activeChannel.current !== msg.channel_id) {
            setUnread((u) => ({
              ...u,
              [msg.channel_id]: (u[msg.channel_id] ?? 0) + 1,
            }));
          }
          break;
        }
        case "chat.updated": {
          const msg = payload as unknown as ChatMessage;
          if (!msg?.channel_id) return;
          qc.setQueryData<InfiniteHistory | undefined>(
            qk.chat.messages(msg.channel_id),
            (old) => patchMessage(old, msg),
          );
          break;
        }
        case "chat.deleted": {
          const msg = payload as unknown as ChatMessage;
          if (!msg?.channel_id) return;
          qc.setQueryData<InfiniteHistory | undefined>(
            qk.chat.messages(msg.channel_id),
            (old) =>
              patchMessage(old, {
                ...msg,
                content: "[deleted]",
                deleted: true,
              }),
          );
          break;
        }
        case "chat.typing": {
          const channelId = payload.channel_id as string | undefined;
          const userId = payload.user_id as string | undefined;
          if (!channelId || !userId) return;
          setTyping((t) => {
            const list = (t[channelId] ?? []).filter(
              (s) => s.userId !== userId,
            );
            return {
              ...t,
              [channelId]: [...list, { channelId, userId, at: Date.now() }],
            };
          });
          break;
        }
        default:
      }
    });
  }, [qc]);

  // Expire typing entries older than 4s.
  React.useEffect(() => {
    const t = setInterval(() => {
      setTyping((cur) => {
        const next: Record<string, TypingState[]> = {};
        const cutoff = Date.now() - 4000;
        for (const [k, v] of Object.entries(cur)) {
          const fresh = v.filter((s) => s.at > cutoff);
          if (fresh.length) next[k] = fresh;
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const typingByChannel = React.useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [k, v] of Object.entries(typing))
      out[k] = v.map((s) => s.userId);
    return out;
  }, [typing]);

  const markRead = React.useCallback((channelId: string) => {
    setUnread((u) => {
      if (!u[channelId]) return u;
      const next = { ...u };
      delete next[channelId];
      return next;
    });
  }, []);

  return { status, typing: typingByChannel, send, unread, markRead };
}

/** @brief Imperative helper to send a chat.message frame. */
export function sendChatMessage(channelId: string, content: string): void {
  chatWs.send({
    type: "chat.message",
    payload: { channel_id: channelId, content },
  });
}

/** @brief Imperative helper to send a chat.typing frame (debounced by caller). */
export function sendChatTyping(channelId: string): void {
  chatWs.send({ type: "chat.typing", payload: { channel_id: channelId } });
}
