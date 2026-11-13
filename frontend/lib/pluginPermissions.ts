/**
 * @file lib/pluginPermissions.ts
 * @brief Human descriptions and sensitivity flags for plugin permissions.
 */

/** @brief Permissions that warrant a warning style. */
export const SENSITIVE_PERMISSIONS = new Set([
  "db_write",
  "send_notifications",
  "external_http",
  "storage_access",
]);

const DESCRIPTIONS: Record<string, string> = {
  db_read: "Read the plugin's own stored data",
  db_write: "Create, change and delete the plugin's stored data",
  hooks_before_post_created: "Inspect or block posts before they are created",
  hooks_after_post_created: "React after a post is created",
  hooks_before_chat_sent: "Inspect or block chat messages before sending",
  hooks_after_chat_sent: "React after a chat message is sent",
  hooks_on_user_joined: "React when a member joins",
  hooks_on_community_created: "React when a community is created",
  send_notifications: "Send notifications to members",
  storage_access: "Read and write files in storage",
  external_http: "Make outbound requests to external servers",
  frontend_routes: "Add pages and UI slots to the app",
  celery_tasks: "Run background tasks",
};

/**
 * @brief Describe a permission.
 * @param perm permission id
 * @return description text
 */
export const describePermission = (perm: string): string =>
  DESCRIPTIONS[perm] ?? "Custom permission";
