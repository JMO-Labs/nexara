/**
 * @file lib/notifications/types.ts
 * @brief Frontend mirror of the backend notification registry / API schemas.
 */
export type Channel = "inapp" | "email" | "push" | "webhook" | "toast";

export type Category =
  | "social"
  | "event"
  | "gallery"
  | "prompt"
  | "system"
  | "plugin";

export type DigestCadence = "instant" | "hourly" | "daily" | "off";

export interface ActionDescriptor {
  key: string;
  label_i18n: string;
  method: "POST" | "PUT" | "DELETE";
  url_template: string;
  style: "primary" | "neutral" | "danger";
}

export interface NotificationTypeDescriptor {
  key: string;
  category: Category;
  default_channels: Record<Channel, boolean>;
  user_configurable: Channel[];
  group_window_seconds: number | null;
  toast_on_arrival: boolean;
  bypass_dnd: boolean;
  digestable: boolean;
  actions: ActionDescriptor[];
  label_i18n: string;
  icon: string;
  plugin_id: string | null;
  payload_schema: Record<string, unknown>;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  type: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  dismissed_at: string | null;
  created_at: string;
  updated_at: string;
  count: number;
  actor_ids: string[];
}

export interface PreferencesPayload {
  notification_prefs: Record<string, Partial<Record<Channel, boolean>>>;
  dnd_schedule: Record<string, { start: string; end: string }[]> | null;
  dnd_until: string | null;
  dnd_timezone: string;
  digest_cadence: Record<string, DigestCadence>;
}

export interface WebhookCreateBody {
  url: string;
  type_keys?: string[];
}

export interface WebhookUpdateBody {
  url?: string;
  type_keys?: string[];
  enabled?: boolean;
}

export interface WebhookListItem {
  id: string;
  url: string;
  type_keys: string[];
  enabled: boolean;
  failure_count: number;
  last_failure_at: string | null;
  created_at: string;
}

/** `secret` is returned only once, on create. */
export interface WebhookCreateResponse {
  id: string;
  url: string;
  secret: string;
  type_keys: string[];
  enabled: boolean;
}
