<!--
  @file components/admin/UserTable.vue
  @brief Admin user management table.

  Displays users with avatar, name, email, role select dropdown, status badge,
  and action dropdown. Role column uses <select> with admin/member/viewer.
  Action dropdown is teleported to body to escape overflow-x-auto clipping.
-->
<template>
  <div class="overflow-x-auto rounded-lg border border-border">
    <table class="w-full min-w-[600px] text-left text-sm">
      <thead class="border-b border-border bg-muted/50">
        <tr>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.actor") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.email") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.role") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.status") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.created") }}
          </th>
          <th class="px-4 py-3 font-medium text-foreground">
            {{ $t("admin.actions") }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading" class="border-b border-border">
          <td colspan="6" class="px-4 py-8 text-center text-muted-foreground">
            {{ $t("common.loading") }}
          </td>
        </tr>
        <tr v-else-if="!users.length" class="border-b border-border">
          <td colspan="6" class="px-4 py-8 text-center text-muted-foreground">
            {{ $t("admin.no_results") }}
          </td>
        </tr>
        <tr
          v-for="u in users"
          :key="u.id"
          class="border-b border-border last:border-0 hover:bg-muted/30"
        >
          <td class="px-4 py-3">
            <div class="flex items-center gap-3">
              <img
                v-if="u.avatar_url"
                :src="u.avatar_url"
                :alt="u.display_name"
                class="h-8 w-8 rounded-full object-cover"
              />
              <div
                v-else
                class="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground"
              >
                {{ (u.display_name || u.username || "?")[0].toUpperCase() }}
              </div>
              <span class="font-medium text-foreground">
                {{ u.display_name || u.username }}
              </span>
            </div>
          </td>
          <td class="px-4 py-3 text-muted-foreground">{{ u.email }}</td>
          <td class="px-4 py-3">
            <select
              :value="u.role"
              class="rounded border border-input bg-background px-2 py-1 text-sm text-foreground focus:ring-2 focus:ring-ring"
              @change="
                onRoleChange(u, ($event.target as HTMLSelectElement).value)
              "
            >
              <option value="admin">admin</option>
              <option value="member">member</option>
              <option value="viewer">viewer</option>
            </select>
          </td>
          <td class="px-4 py-3">
            <span
              class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
              :class="statusBadgeClass(u)"
            >
              {{ userStatus(u) }}
            </span>
          </td>
          <td class="px-4 py-3 text-muted-foreground">
            {{ formatDate(u.created_at) }}
          </td>
          <td class="px-4 py-3">
            <button
              :ref="(el) => setTriggerRef(u.id, el as HTMLElement | null)"
              type="button"
              class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-haspopup="true"
              :aria-expanded="openDropdown === u.id"
              @click.stop="toggleDropdown(u.id)"
            >
              <span aria-hidden="true">&#x22EE;</span>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Action dropdown teleported to body to escape overflow clipping -->
  <Teleport to="body">
    <div
      v-if="openDropdown !== null"
      class="fixed inset-0 z-[9998]"
      @click="openDropdown = null"
    />
    <div
      v-if="openDropdown !== null"
      class="fixed z-[9999] min-w-[140px] rounded-lg border border-border bg-popover py-1 shadow-xl"
      :style="dropdownStyle"
      @click.stop
    >
      <button
        v-if="activeUser?.status !== 'suspended'"
        type="button"
        class="block w-full px-4 py-2 text-left text-sm hover:bg-muted"
        @click="handleAction('suspend')"
      >
        {{ $t("admin.suspend") }}
      </button>
      <button
        v-else
        type="button"
        class="block w-full px-4 py-2 text-left text-sm hover:bg-muted"
        @click="handleAction('restore')"
      >
        {{ $t("admin.restore") }}
      </button>
      <button
        type="button"
        class="block w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-muted dark:text-red-400"
        @click="handleAction('delete')"
      >
        {{ $t("common.delete") }}
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief UserTable with role/status badges and teleported action dropdown.
 */
import { ref, computed, onUnmounted } from "vue";
import type { AdminUserListItem, UserRole } from "~/types/api";

const { t: $t } = useI18n();

const props = defineProps<{
  /** @brief List of users to display. */
  users: AdminUserListItem[];
  /** @brief Whether data is loading. */
  loading?: boolean;
}>();

const emit = defineEmits<{
  "change-role": [user: AdminUserListItem, role: UserRole];
  suspend: [user: AdminUserListItem];
  restore: [user: AdminUserListItem];
  delete: [user: AdminUserListItem];
}>();

/** @brief ID of user whose dropdown is open. */
const openDropdown = ref<string | null>(null);

/** @brief Map of user IDs to their trigger button elements. */
const triggerRefs = new Map<string, HTMLElement>();

/** @brief Absolute position for the teleported dropdown. */
const dropdownPos = ref({ top: 0, left: 0 });

/** @brief The user whose action dropdown is currently open. */
const activeUser = computed(() =>
  openDropdown.value
    ? props.users.find((u) => u.id === openDropdown.value)
    : null,
);

/** @brief CSS style object positioning the dropdown near the trigger button. */
const dropdownStyle = computed(() => ({
  top: `${dropdownPos.value.top}px`,
  left: `${dropdownPos.value.left}px`,
}));

/** @brief Store a reference to a trigger button element by user ID. */
function setTriggerRef(id: string, el: HTMLElement | null): void {
  if (el) {
    triggerRefs.set(id, el);
  } else {
    triggerRefs.delete(id);
  }
}

/** @brief Toggle the action dropdown and compute its position. */
function toggleDropdown(id: string): void {
  if (openDropdown.value === id) {
    openDropdown.value = null;
    return;
  }
  const trigger = triggerRefs.get(id);
  if (trigger) {
    const rect = trigger.getBoundingClientRect();
    dropdownPos.value = {
      top: rect.bottom + 4,
      left: Math.max(rect.right - 140, 8),
    };
  }
  openDropdown.value = id;
}

/** @brief Dispatch an action for the active user and close the dropdown. */
function handleAction(action: "suspend" | "restore" | "delete"): void {
  if (!activeUser.value) return;
  emit(action, activeUser.value);
  openDropdown.value = null;
}

/** @brief Emit change-role when role select changes. */
function onRoleChange(user: AdminUserListItem, newRole: string): void {
  if (
    newRole &&
    (newRole === "admin" || newRole === "member" || newRole === "viewer") &&
    newRole !== user.role
  ) {
    emit("change-role", user, newRole as UserRole);
  }
}

/** @brief Status badge color classes. */
function statusBadgeClass(u: AdminUserListItem): string {
  const status = u.status ?? "active";
  return status === "suspended"
    ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
    : "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
}

/** @brief Human-readable status. */
function userStatus(u: AdminUserListItem): string {
  return u.status === "suspended" ? $t("admin.suspended") : $t("admin.active");
}

/** @brief Format created_at for display. */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

onUnmounted(() => {
  triggerRefs.clear();
});
</script>
