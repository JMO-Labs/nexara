/**
 * @file lib/api/chatContext.ts
 * @brief Conversation details (details panel) client.
 */
import { apiGet, seg } from "./client";

export interface ContextEvent {
  id: string;
  title: string;
  starts_at: string;
}
export interface ContextMedia {
  id: string;
  thumb_url: string;
}
export interface DmContext {
  kind: "dm";
  peer: {
    id: string;
    display_name: string;
    username: string;
    avatar_url: string | null;
    last_seen_at: string | null;
    local_time_tz: string | null;
    birthday_in_days: number | null;
  };
  shared_groups: { id: string; name: string; slug: string }[];
  upcoming_events: ContextEvent[];
  recent_media: ContextMedia[];
}
export interface GroupContext {
  kind: "group";
  members: { id: string; display_name: string; avatar_url: string | null }[];
  member_count: number;
  next_event: ContextEvent | null;
  open_lists: { id: string; title: string; item_count: number }[];
  recent_media: ContextMedia[];
}
export type ChatContext = DmContext | GroupContext;

/**
 * @brief Fetch details for a channel the viewer participates in.
 * @param channelId channel id
 * @return DM or group context
 */
export const getChatContext = (channelId: string) =>
  apiGet<ChatContext>(`/api/v1/chat/channels/${seg(channelId)}/context`);
