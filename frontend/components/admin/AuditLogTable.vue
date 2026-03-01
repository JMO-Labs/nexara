<!--
  @file components/admin/AuditLogTable.vue
  @brief Admin audit log table.

  Displays audit entries with time (relative), actor, action badge,
  target, and IP. Responsive table design.
-->
<template>
  <div class="overflow-x-auto rounded-lg border border-border">
    <table class="w-full min-w-[500px] text-left text-sm">
      <thead class="border-b border-border bg-muted/50">
        <tr>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.time") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.actor") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.action") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.target") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.ip") }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading" class="border-b border-border">
          <td colspan="5" class="px-4 py-8 text-center text-muted-foreground">
            {{ $t("common.loading") }}
          </td>
        </tr>
        <tr v-else-if="!entries.length" class="border-b border-border">
          <td colspan="5" class="px-4 py-8 text-center text-muted-foreground">
            {{ $t("admin.no_results") }}
          </td>
        </tr>
        <tr
          v-for="e in entries"
          :key="e.id"
          class="border-b border-border last:border-0 hover:bg-muted/30"
        >
          <td class="px-4 py-3 text-muted-foreground">
            {{ formatRelative(e.created_at) }}
          </td>
          <td class="px-4 py-3 font-medium text-foreground">
            {{ e.actor_display_name ?? $t("settings.system") }}
          </td>
          <td class="px-4 py-3">
            <span
              class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
              :class="actionBadgeClass(e.action)"
            >
              {{ actionLabel(e.action) }}
            </span>
          </td>
          <td class="px-4 py-3 text-muted-foreground">
            {{ e.target_display ?? e.target_type ?? "—" }}
          </td>
          <td class="px-4 py-3 font-mono text-xs text-muted-foreground">
            {{ e.ip_address ?? "—" }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief AuditLogTable with relative time formatting.
 */
import type { AuditLogEntry } from "~/types/api";

const { t, te } = useI18n();

/** @brief Badge color classes keyed by action prefix. */
const ACTION_STYLES: Record<string, string> = {
  "admin.user.suspended":
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  "admin.user.deleted":
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  "admin.user.restored":
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  "admin.user.role_changed":
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  "admin.settings":
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  branding:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  invite: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400",
};

/**
 * @brief Resolve a human-readable label for an audit action key.
 * @param action Raw action key from backend (e.g. "admin.user.role_changed").
 */
function actionLabel(action: string): string {
  const key = `admin.auditActions.${action}`;
  return te(key)
    ? t(key)
    : (action.split(".").pop()?.replace(/_/g, " ") ?? action);
}

/**
 * @brief Return Tailwind badge classes for the given action.
 * @param action Raw action key from backend.
 */
function actionBadgeClass(action: string): string {
  if (ACTION_STYLES[action]) return ACTION_STYLES[action];
  for (const prefix of Object.keys(ACTION_STYLES)) {
    if (action.startsWith(prefix)) return ACTION_STYLES[prefix];
  }
  return "bg-muted text-foreground";
}

defineProps<{
  /** @brief List of audit log entries. */
  entries: AuditLogEntry[];
  /** @brief Whether data is loading. */
  loading?: boolean;
}>();

/** @brief Format timestamp as relative time (e.g. "2 min ago"). */
function formatRelative(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHr / 24);

    if (diffSec < 60) return t("admin.justNow");
    if (diffMin < 60) return t("admin.minutesAgo", { count: diffMin });
    if (diffHr < 24) return t("admin.hoursAgo", { count: diffHr });
    if (diffDay < 7) return t("notifications.daysAgo", { count: diffDay });
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
</script>
