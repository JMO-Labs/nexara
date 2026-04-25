/**
 * @file types/events.ts
 * @brief Shared event type constants and payload interfaces for SSE.
 *
 * Mirrors the backend event types defined in
 * ``backend/app/services/realtime/events.py``.  Used by stores and
 * composables to avoid magic strings when registering handlers.
 */

/** @brief Top-level SSE event type names (wire format). */
export const SSE_EVENT = {
  FEED_UPDATE: "feed_update",
  NOTIFICATION: "notification",
  TYPING: "typing",
  PRESENCE: "presence",
} as const;

/** @brief Sub-event discriminator within ``feed_update`` payloads. */
export const FEED_EVENT = {
  POST_CREATED: "created",
  COMMENT_CREATED: "comment_created",
  REACTION_TOGGLED: "reaction_toggled",
} as const;

/** @brief Union of valid SSE event type values. */
export type SseEventType = (typeof SSE_EVENT)[keyof typeof SSE_EVENT];

/** @brief Union of valid feed sub-event values. */
export type FeedEventType = (typeof FEED_EVENT)[keyof typeof FEED_EVENT];

/** @brief Payload shape for all ``feed_update`` SSE events. */
export interface FeedUpdatePayload {
  event: FeedEventType | string;
  [key: string]: unknown;
}

/** @brief Payload for a ``reaction_toggled`` feed event. */
export interface ReactionToggledPayload {
  event: typeof FEED_EVENT.REACTION_TOGGLED;
  post_id: string;
  target_type: "post" | "comment";
  target_id: string;
  emoji: string;
  count: number;
  action: "added" | "removed";
  user_id: string;
}

/** @brief Payload for a ``comment_created`` feed event. */
export interface CommentCreatedPayload {
  event: typeof FEED_EVENT.COMMENT_CREATED;
  post_id: string;
  comment: import("~/types/api").Comment;
  user_id: string;
}

/** @brief Payload for a ``created`` (new post) feed event. */
export interface PostCreatedPayload {
  event: typeof FEED_EVENT.POST_CREATED;
  post: import("~/types/api").Post;
}

/** @brief Chat WebSocket frame type names (wire format). */
export const CHAT_EVENT = {
  MESSAGE: "chat.message",
  UPDATED: "chat.updated",
  DELETED: "chat.deleted",
  TYPING: "chat.typing",
  READ: "chat.read",
  ERROR: "chat.error",
} as const;

/** @brief Union of valid chat WS event type values. */
export type ChatEventType = (typeof CHAT_EVENT)[keyof typeof CHAT_EVENT];

/**
 * @brief Generic envelope for chat WebSocket frames.
 *
 * Matches the backend realtime envelope `{type, payload, ts}`.
 */
export interface ChatWsFrame<T = unknown> {
  type: ChatEventType | string;
  payload: T;
  ts?: string;
}
