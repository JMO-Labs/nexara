/**
 * @file lib/api/settings.ts
 * @brief User settings endpoints: profile, notifications, appearance, email.
 */
import { apiGet, apiPut } from "./client";
import type { HomePattern } from "@/lib/patterns";

export interface PrivacyAppearanceSettings {
  profile_visible_to: "community" | "admin_only";
  show_online_status: boolean;
  show_last_seen: boolean;
  show_birthday_to: "nobody" | "community" | "admin_only";
  show_birthday_year: boolean;
  allow_sassybot: boolean;
  font_size: "small" | "medium" | "large";
  compact_feed: boolean;
}

export interface UserSettings extends PrivacyAppearanceSettings {
  theme: "system" | "light" | "dark";
  locale: string;
  notif_mention_inapp: boolean;
  notif_mention_email: boolean;
  notif_comment_inapp: boolean;
  notif_comment_email: boolean;
  notif_reaction_inapp: boolean;
  notif_reaction_email: boolean;
  notif_new_post_inapp: boolean;
  notif_new_post_email: boolean;
  notif_system_inapp: boolean;
  notif_system_email: boolean;
  notif_invite_accepted_inapp: boolean;
  notif_invite_accepted_email: boolean;
  mute_all_email: boolean;
  home_pattern?: HomePattern | null;
  reduce_transparency?: boolean;
  receive_nudges?: boolean;
  receive_gentle_nudges?: boolean;
}

export type NotificationType =
  | "mention"
  | "comment"
  | "reaction"
  | "new_post"
  | "system"
  | "invite_accepted"
  | "event_reminder"
  | "event_rsvp"
  | "gallery_activity"
  | "prompt"
  | "prompt_summary"
  | "poll"
  | "dm"
  | "birthday";

export type NotificationChannel = "inapp" | "email" | "push";

/** All 42 notif_<type>_<channel> flags. */
export type NotificationChannelFlags = Record<
  `notif_${NotificationType}_${NotificationChannel}`,
  boolean
>;

export interface NotificationPreferences extends NotificationChannelFlags {
  mute_all_email: boolean;
  mute_all_push: boolean;
  email_digest_enabled: boolean;
  /** Local hour of day (0-23) for the digest. */
  email_digest_hour: number;
  /** Per-type Apprise channel flags, e.g. notif_mention_apprise. */
  [apprise: `notif_${string}_apprise`]: boolean | undefined;
}

export interface UserSettingsUpdate extends Partial<PrivacyAppearanceSettings> {
  theme?: "system" | "light" | "dark";
  locale?: string;
  home_pattern?: HomePattern | null;
  reduce_transparency?: boolean;
  receive_nudges?: boolean;
  receive_gentle_nudges?: boolean;
}

export interface ProfileUpdate {
  /** Opt in/out of showing your Gravatar (server stores the URL). */
  use_gravatar?: boolean;
  /** Uploaded photo; null removes it. */
  avatar_media_id?: string | null;
  display_name?: string;
  bio?: string;
  location?: string;
  website_url?: string;
  title?: string;
  pronouns?: string;
  birthday?: string | null;
  banner_media_id?: string | null;
  phone?: string;
  contact_email?: string;
  address?: string;
  links?: { label: string; url: string }[];
  emergency_contact?: { name: string; phone: string; relation: string } | null;
  skills?: string[];
  availability?: string;
  dietary?: string;
  field_visibility?: Record<string, "private" | "groups" | "community">;
}

export interface MessageResponse {
  message: string;
}

const SETTINGS = "/api/v1/settings";

/**
 * @brief Get current user's settings.
 * @return UserSettings object with theme, locale, and notification preferences.
 */
export const getSettings = () => apiGet<UserSettings>(`${SETTINGS}/`);

/**
 * @brief Update settings (theme, locale).
 * @param body Partial UserSettingsUpdate object.
 * @return Updated UserSettings.
 */
export const updateSettings = (body: Partial<UserSettingsUpdate>) =>
  apiPut<UserSettings>(`${SETTINGS}/`, body);

/**
 * @brief Get notification preferences.
 * @return NotificationPreferences object.
 */
export const getNotificationPrefs = () =>
  apiGet<NotificationPreferences>(`${SETTINGS}/notifications`);

/**
 * @brief Update notification preferences.
 * @param body Partial NotificationPreferences object.
 * @return Updated UserSettings.
 */
export const updateNotificationPrefs = (
  body: Partial<NotificationPreferences>,
) => apiPut<UserSettings>(`${SETTINGS}/notifications`, body);

/**
 * @brief Update user profile information.
 * @param body Partial ProfileUpdate object.
 * @return MessageResponse confirming update.
 */
export const updateProfile = (body: Partial<ProfileUpdate>) =>
  apiPut<MessageResponse>(`${SETTINGS}/profile`, body);

/**
 * @brief Update user email address.
 * @param email New email address.
 * @return MessageResponse confirming update.
 */
export const updateEmail = (email: string) =>
  apiPut<MessageResponse>(`${SETTINGS}/email`, { email });
