<!--
  @file pages/app/subgroups/[slug]/members.vue
  @brief Subgroup member list with role and remove controls.

  Fetches the membership list for the subgroup identified by the route
  `slug` param. Owners, moderators, and community admins can change
  member roles (owner-only for promoting to owner) and remove members.
  All actions route through the subgroups Pinia store.
-->
<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-2">
      <div>
        <NuxtLink
          :to="`/app/subgroups/${slug}`"
          data-testid="members-back"
          class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <span aria-hidden="true">&larr;</span>
          {{ $t("subgroups.backToDirectory") }}
        </NuxtLink>
        <h1 class="text-2xl font-bold text-foreground">
          {{ $t("subgroups.membersTitle") }}
        </h1>
      </div>
    </div>

    <div
      v-if="loading && members.length === 0"
      class="rounded-lg border border-border bg-card p-6 text-center text-muted-foreground"
      data-testid="members-loading"
    >
      {{ $t("common.loading") }}
    </div>

    <div
      v-else-if="members.length === 0"
      class="rounded-lg border border-dashed border-border bg-card p-6 text-center text-muted-foreground"
      data-testid="members-empty"
    >
      {{ $t("common.noResults") }}
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full min-w-[500px] text-left text-sm">
        <thead class="border-b border-border bg-muted/50">
          <tr>
            <th class="px-4 py-3 font-medium text-foreground">
              {{ $t("subgroups.membersTitle") }}
            </th>
            <th class="px-4 py-3 font-medium text-foreground">
              {{ $t("subgroups.role.member") }}
            </th>
            <th class="px-4 py-3 font-medium text-foreground" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in members"
            :key="m.user_id"
            :data-testid="`member-row-${m.user_id}`"
            class="border-b border-border last:border-0 hover:bg-muted/30"
          >
            <td class="px-4 py-3">
              <div class="flex items-center gap-3">
                <img
                  v-if="m.avatar_url"
                  :src="m.avatar_url"
                  :alt="m.display_name ?? m.username ?? ''"
                  class="h-8 w-8 rounded-full object-cover"
                />
                <div
                  v-else
                  class="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground"
                  aria-hidden="true"
                >
                  {{
                    (m.display_name || m.username || "?")[0].toUpperCase()
                  }}
                </div>
                <div class="min-w-0">
                  <p class="font-medium text-foreground">
                    {{ m.display_name || m.username }}
                  </p>
                  <p class="text-xs text-muted-foreground">
                    @{{ m.username }}
                  </p>
                </div>
              </div>
            </td>
            <td class="px-4 py-3">
              <select
                v-if="canManage && m.user_id !== currentUserId"
                :value="m.role"
                :data-testid="`member-role-${m.user_id}`"
                :aria-label="$t('subgroups.changeRole')"
                class="rounded border border-input bg-background px-2 py-1 text-sm text-foreground focus:ring-2 focus:ring-ring"
                @change="
                  onRoleChange(m.user_id, ($event.target as HTMLSelectElement).value)
                "
              >
                <option value="owner">
                  {{ $t("subgroups.role.owner") }}
                </option>
                <option value="moderator">
                  {{ $t("subgroups.role.moderator") }}
                </option>
                <option value="member">
                  {{ $t("subgroups.role.member") }}
                </option>
              </select>
              <span
                v-else
                class="inline-flex rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
              >
                {{ $t(`subgroups.role.${m.role}`) }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="canManage && m.user_id !== currentUserId"
                type="button"
                :data-testid="`member-remove-${m.user_id}`"
                :aria-label="$t('subgroups.removeMember')"
                class="rounded-md border border-border px-3 py-1 text-xs text-red-600 hover:bg-destructive/10 dark:text-red-400"
                @click="confirmRemove(m.user_id)"
              >
                {{ $t("subgroups.removeMember") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Members page for a single subgroup.
 */
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useSubgroupsStore } from "~/stores/subgroups";
import { useAuthStore } from "~/stores/auth";
import { useUiStore } from "~/stores/ui";
import type { SubgroupRole } from "~/types/api";

const route = useRoute();
const subgroupsStore = useSubgroupsStore();
const authStore = useAuthStore();
const uiStore = useUiStore();
const { t: $t } = useI18n();

const slug = computed(() => String(route.params.slug ?? ""));
const members = computed(() => subgroupsStore.members);
const loading = computed(() => subgroupsStore.loading);

/** @brief Current viewer's user ID (used to hide self-destructive controls). */
const currentUserId = computed(() => authStore.user?.id ?? "");

/**
 * @brief Whether the viewer can manage members (change roles, remove).
 *
 * Owners and moderators can manage; community admins always can.
 * Backend enforces this; the UI hides controls for clarity.
 */
const canManage = computed(() => {
  if (authStore.user?.role === "admin") return true;
  const myRole = subgroupsStore.current?.my_role;
  return myRole === "owner" || myRole === "moderator";
});

/** @brief Validate an arbitrary string is a valid subgroup role. */
function isRole(value: string): value is SubgroupRole {
  return value === "owner" || value === "moderator" || value === "member";
}

/** @brief Handle role change from the select. */
async function onRoleChange(userId: string, value: string): Promise<void> {
  if (!isRole(value)) return;
  try {
    await subgroupsStore.changeMemberRole(slug.value, userId, value);
    uiStore.showToast({
      type: "success",
      message: $t("subgroups.roleUpdated"),
    });
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  }
}

/** @brief Prompt-confirm and remove the given member. */
async function confirmRemove(userId: string): Promise<void> {
  if (!confirm($t("subgroups.removeMemberConfirm"))) return;
  try {
    await subgroupsStore.removeMember(slug.value, userId);
    uiStore.showToast({
      type: "success",
      message: $t("subgroups.memberRemoved"),
    });
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  }
}

async function load(): Promise<void> {
  if (!slug.value) return;
  try {
    // Ensure we have current.my_role for canManage gating.
    if (subgroupsStore.current?.slug !== slug.value) {
      await subgroupsStore.fetchDetail(slug.value);
    }
    await subgroupsStore.fetchMembers(slug.value);
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  }
}

onMounted(load);
</script>
