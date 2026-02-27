<!--
  @file components/admin/UserTable.vue
  @brief Admin user management table.

  Displays users with avatar, name, email, role badge, status, and actions.
  Emits change-role, suspend, restore, delete for row actions.
-->
<template>
  <div class="overflow-x-auto rounded-lg border border-border">
    <table class="w-full min-w-[600px] text-left text-sm">
      <thead class="border-b border-border bg-muted/50">
        <tr>
          <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.actor') }}</th>
          <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.email') }}</th>
          <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.role') }}</th>
          <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.status') }}</th>
          <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.created') }}</th>
          <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.actions') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-if="loading"
          class="border-b border-border"
        >
          <td
            colspan="6"
            class="px-4 py-8 text-center text-muted-foreground"
          >
            {{ $t('common.loading') }}
          </td>
        </tr>
        <tr
          v-else-if="!users.length"
          class="border-b border-border"
        >
          <td
            colspan="6"
            class="px-4 py-8 text-center text-muted-foreground"
          >
            {{ $t('admin.no_results') }}
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
              >
              <div
                v-else
                class="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground"
              >
                {{ (u.display_name || u.username || '?')[0].toUpperCase() }}
              </div>
              <span class="font-medium text-foreground">
                {{ u.display_name || u.username }}
              </span>
            </div>
          </td>
          <td class="px-4 py-3 text-muted-foreground">{{ u.email }}</td>
          <td class="px-4 py-3">
            <span
              class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
              :class="roleBadgeClass(u.role)"
            >
              {{ u.role }}
            </span>
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
            <div class="relative">
              <button
                type="button"
                class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-haspopup="true"
                aria-expanded="openDropdown === u.id"
                @click.stop="toggleDropdown(u.id)"
              >
                <span aria-hidden="true">⋮</span>
              </button>
              <div
                v-if="openDropdown === u.id"
                class="absolute right-0 top-full z-10 mt-1 min-w-[140px] rounded-lg border border-border bg-card py-1 shadow-lg"
                @click.stop
              >
                <button
                  type="button"
                  class="block w-full px-4 py-2 text-left text-sm hover:bg-muted"
                  @click="emit('change-role', u); openDropdown = null"
                >
                  {{ $t('admin.change_role') }}
                </button>
                <button
                  v-if="u.status !== 'suspended'"
                  type="button"
                  class="block w-full px-4 py-2 text-left text-sm hover:bg-muted"
                  @click="emit('suspend', u); openDropdown = null"
                >
                  {{ $t('admin.suspend') }}
                </button>
                <button
                  v-else
                  type="button"
                  class="block w-full px-4 py-2 text-left text-sm hover:bg-muted"
                  @click="emit('restore', u); openDropdown = null"
                >
                  {{ $t('admin.restore') }}
                </button>
                <button
                  type="button"
                  class="block w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-muted dark:text-red-400"
                  @click="emit('delete', u); openDropdown = null"
                >
                  {{ $t('common.delete') }}
                </button>
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief UserTable with role/status badges and action dropdown.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import type { AdminUserListItem, UserRole } from '~/types/api'

const { t: $t } = useI18n()

defineProps<{
  /** @brief List of users to display. */
  users: AdminUserListItem[]
  /** @brief Whether data is loading. */
  loading?: boolean
}>()

const emit = defineEmits<{
  'change-role': [user: AdminUserListItem]
  suspend: [user: AdminUserListItem]
  restore: [user: AdminUserListItem]
  delete: [user: AdminUserListItem]
}>()

/** @brief ID of user whose dropdown is open. */
const openDropdown = ref<string | null>(null)

/** @brief Role badge color classes. */
function roleBadgeClass(role: UserRole): string {
  const map: Record<UserRole, string> = {
    admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
    member: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    viewer: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  }
  return map[role] ?? 'bg-gray-100 text-gray-800'
}

/** @brief Status badge color classes. */
function statusBadgeClass(u: AdminUserListItem): string {
  const status = u.status ?? 'active'
  return status === 'suspended'
    ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
    : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
}

/** @brief Human-readable status. */
function userStatus(u: AdminUserListItem): string {
  return u.status === 'suspended' ? $t('admin.suspended') : $t('admin.active')
}

/** @brief Format created_at for display. */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return iso
  }
}

function toggleDropdown(id: string): void {
  openDropdown.value = openDropdown.value === id ? null : id
}

function handleClickOutside(): void {
  openDropdown.value = null
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
