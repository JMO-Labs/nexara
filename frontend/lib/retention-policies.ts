/**
 * @file lib/retention-policies.ts
 * @brief Retention policy types, friendly labels, and client-side limits.
 */

/** @brief Retention policy as returned by the admin API. */
export interface RetentionPolicy {
  policy_key: string;
  enabled: boolean;
  retention_days: number | null;
  delete_media_files: boolean;
  updated_at: string;
  updated_by: string | null;
}

/** @brief Editable subset sent on PUT. */
export type RetentionUpdate = Pick<
  RetentionPolicy,
  "enabled" | "retention_days" | "delete_media_files"
>;

export interface PolicyMeta {
  label: string;
  /** Minimum days when a value is set. */
  min: number;
  /** Whether days may be empty (keep forever / expiry-driven). */
  allowForever: boolean;
  /** Opt-in policy that permanently deletes user content. */
  dangerous?: boolean;
  /** Policy may remove media files from storage. */
  media?: boolean;
}

/** @brief Metadata for all 12 policy types. */
export const POLICY_META: Record<string, PolicyMeta> = {
  chat_messages: { label: "Chat Messages", min: 30, allowForever: false },
  notifications: { label: "Notifications", min: 7, allowForever: false },
  soft_deleted_posts: {
    label: "Soft-deleted Posts",
    min: 7,
    allowForever: false,
    media: true,
  },
  soft_deleted_media: {
    label: "Soft-deleted Media",
    min: 7,
    allowForever: false,
    media: true,
  },
  soft_deleted_users: {
    label: "Soft-deleted Users",
    min: 7,
    allowForever: false,
  },
  link_preview_cache: {
    label: "Link Preview Cache",
    min: 1,
    allowForever: false,
  },
  audit_logs: { label: "Audit Logs", min: 365, allowForever: false },
  auth_tokens: { label: "Auth Tokens", min: 1, allowForever: true },
  ai_usage_logs: { label: "AI Usage Logs", min: 7, allowForever: false },
  orphaned_media: {
    label: "Orphaned Media",
    min: 1,
    allowForever: false,
    media: true,
  },
  post_media_age: {
    label: "Post Media Age",
    min: 30,
    allowForever: true,
    dangerous: true,
    media: true,
  },
  post_age: {
    label: "Post Age",
    min: 30,
    allowForever: true,
    dangerous: true,
    media: true,
  },
};

/**
 * @brief Friendly label for a policy key.
 * @param key policy_key
 * @return label, or the key when unknown
 */
export const policyLabel = (key: string) => POLICY_META[key]?.label ?? key;

/**
 * @brief Validate a retention-days value for a policy.
 * @param key policy_key
 * @param days value, null for keep forever
 * @return error message or null when valid
 */
export function validateDays(key: string, days: number | null): string | null {
  const meta = POLICY_META[key];
  if (days === null) {
    return meta && !meta.allowForever ? "Enter a number of days" : null;
  }
  if (!Number.isInteger(days)) return "Must be a whole number of days";
  const min = meta?.min ?? 1;
  return days < min ? `Must be at least ${min} days` : null;
}
