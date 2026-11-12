/**
 * @file lib/api/chat.ts
 * @brief Chat REST endpoints (channels, history, DMs).
 */
import { apiGet, apiPost, apiDelete, seg } from "./client";

export interface ChatAuthor {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export type ChannelType = "community" | "subgroup" | "direct";

export interface ChatChannel {
  id: string;
  name: string;
  channel_type: ChannelType;
  subgroup_id: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  channel_id: string;
  author: ChatAuthor | null;
  content: string;
  edited_at: string | null;
  deleted: boolean;
  created_at: string;
}

export interface MessageHistoryPage {
  items: ChatMessage[];
  cursor: string | null;
  has_more: boolean;
}

export interface DmThread {
  channel_id: string;
  peer: ChatAuthor;
  created_at: string;
}

export const listChannels = () =>
  apiGet<ChatChannel[]>("/api/v1/chat/channels");

export const getMessageHistory = (
  channelId: string,
  cursor?: string | null,
  limit = 50,
) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<MessageHistoryPage>(
    `/api/v1/chat/channels/${seg(channelId)}/messages?${qs}`,
  );
};

export const createOrGetDm = (peerId: string) =>
  apiPost<ChatChannel>(`/api/v1/chat/dm/${seg(peerId)}`, {});

export const ensureSubgroupChannel = (subgroupId: string) =>
  apiPost<ChatChannel>(`/api/v1/chat/subgroup/${seg(subgroupId)}`, {});

export const listDmThreads = () => apiGet<DmThread[]>("/api/v1/chat/dm");

export const deleteDmThread = (channelId: string) =>
  apiDelete<void>(`/api/v1/chat/dm/${seg(channelId)}`);
