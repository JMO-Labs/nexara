<!--
  @file pages/app/admin/users.vue
  @brief Admin user management page.

  Searchable table of users with role/status and action dropdown.
  Uses /admin/users API with pagination and search.
-->
<template>
  <div class="space-y-4">
    <div
      class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <input
        v-model="searchQuery"
        type="search"
        :placeholder="$t('common.search')"
        class="max-w-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
        @input="debouncedSearch"
      />
    </div>

    <AdminUserTable
      :users="users"
      :loading="loading"
      @change-role="handleChangeRole"
      @suspend="handleSuspend"
      @restore="handleRestore"
      @delete="handleDelete"
    />

    <div v-if="hasMore && !loading" class="flex justify-center">
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        @click="loadMore"
      >
        {{ $t("feed.loadMore") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin users page with search and pagination.
 */
import { ref, onMounted } from "vue";
import { useApi } from "~/composables/useApi";
import { useUiStore } from "~/stores/ui";
import type { AdminUserListItem, AdminUsersResponse } from "~/types/api";

const api = useApi();
const uiStore = useUiStore();
const { t: $t } = useI18n();

const users = ref<AdminUserListItem[]>([]);
const loading = ref(false);
const searchQuery = ref("");
const cursor = ref<string | null>(null);
const hasMore = ref(false);

let searchTimeout: ReturnType<typeof setTimeout> | null = null;

function debouncedSearch(): void {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    cursor.value = null;
    fetchUsers();
  }, 300);
}

async function fetchUsers(): Promise<void> {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (searchQuery.value) params.set("search", searchQuery.value);
    if (cursor.value) params.set("cursor", cursor.value);
    params.set("limit", "20");
    const res = await api.get<AdminUsersResponse>(
      `/admin/users?${params.toString()}`,
    );
    const items = res?.items ?? [];
    if (!cursor.value) users.value = items;
    else users.value.push(...items);
    cursor.value = res?.next_cursor ?? res?.cursor ?? null;
    hasMore.value = res?.has_more ?? false;
  } catch {
    users.value = [];
    hasMore.value = false;
  } finally {
    loading.value = false;
  }
}

function loadMore(): void {
  if (cursor.value) fetchUsers();
}

async function handleChangeRole(
  user: AdminUserListItem,
  role: string,
): Promise<void> {
  if (!role || !["admin", "member", "viewer"].includes(role)) return;
  try {
    await api.put(`/admin/users/${user.id}/role`, { role });
    uiStore.showToast({ type: "success", message: $t("admin.roleUpdated") });
    await fetchUsers();
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  }
}

async function handleSuspend(user: AdminUserListItem): Promise<void> {
  try {
    await api.post(`/admin/users/${user.id}/suspend`);
    uiStore.showToast({ type: "success", message: $t("admin.userSuspended") });
    await fetchUsers();
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  }
}

async function handleRestore(user: AdminUserListItem): Promise<void> {
  try {
    await api.post(`/admin/users/${user.id}/restore`);
    uiStore.showToast({ type: "success", message: $t("admin.userRestored") });
    await fetchUsers();
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  }
}

async function handleDelete(user: AdminUserListItem): Promise<void> {
  if (!confirm($t("feed.deleteConfirm"))) return;
  try {
    await api.del(`/admin/users/${user.id}`);
    uiStore.showToast({ type: "success", message: $t("admin.userDeleted") });
    await fetchUsers();
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : $t("common.error"),
    });
  }
}

onMounted(() => {
  fetchUsers();
});
</script>
