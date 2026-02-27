<!--
  @file pages/app/admin/invites.vue
  @brief Admin invite management page.

  Create invite form and table of existing invites.
  Uses POST /admin/invites, GET /admin/invites, DELETE /admin/invites/:id.
-->
<template>
  <div class="space-y-6">
    <div class="rounded-lg border border-border bg-card p-6">
      <h2 class="mb-4 text-lg font-semibold text-foreground">
        {{ $t('admin.create_invite') }}
      </h2>
      <form
        class="flex flex-wrap items-end gap-4"
        @submit.prevent="handleCreateInvite"
      >
        <div class="min-w-[200px] flex-1">
          <label
            for="invite_email"
            class="mb-1 block text-sm font-medium text-foreground"
          >
            {{ $t('admin.email') }}
          </label>
          <input
            id="invite_email"
            v-model="createForm.email"
            type="email"
            required
            class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
          >
        </div>
        <div class="min-w-[120px]">
          <label
            for="invite_role"
            class="mb-1 block text-sm font-medium text-foreground"
          >
            {{ $t('admin.role') }}
          </label>
          <select
            id="invite_role"
            v-model="createForm.role"
            class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
          >
            <option value="member">member</option>
            <option value="admin">admin</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <button
          type="submit"
          :disabled="createLoading"
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {{ createLoading ? $t('common.loading') : $t('admin.create_invite') }}
        </button>
      </form>
    </div>

    <div class="rounded-lg border border-border">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[500px] text-left text-sm">
          <thead class="border-b border-border bg-muted/50">
            <tr>
              <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.email') }}</th>
              <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.role') }}</th>
              <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.status') }}</th>
              <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.created') }}</th>
              <th class="px-4 py-3 font-medium text-foreground">{{ $t('admin.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="listLoading" class="border-b border-border">
              <td colspan="5" class="px-4 py-8 text-center text-muted-foreground">
                {{ $t('common.loading') }}
              </td>
            </tr>
            <tr v-else-if="!invites.length" class="border-b border-border">
              <td colspan="5" class="px-4 py-8 text-center text-muted-foreground">
                {{ $t('admin.no_results') }}
              </td>
            </tr>
            <tr
              v-for="inv in invites"
              :key="inv.id"
              class="border-b border-border last:border-0 hover:bg-muted/30"
            >
              <td class="px-4 py-3 text-foreground">{{ inv.email }}</td>
              <td class="px-4 py-3">
                <span class="rounded-full bg-muted px-2 py-0.5 text-xs">
                  {{ inv.role }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="statusClass(inv.status)"
                >
                  {{ $t(`admin.${inv.status}`) }}
                </span>
              </td>
              <td class="px-4 py-3 text-muted-foreground">
                {{ formatDate(inv.created_at) }}
              </td>
              <td class="px-4 py-3">
                <button
                  v-if="inv.status === 'active'"
                  type="button"
                  class="text-sm text-red-600 hover:underline dark:text-red-400"
                  @click="handleRevoke(inv)"
                >
                  {{ $t('admin.revoke') }}
                </button>
                <span v-else class="text-muted-foreground">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin invites page with create form and list.
 */
import { ref, onMounted } from 'vue'
import { useApi } from '~/composables/useApi'
import { useUiStore } from '~/stores/ui'
import type { InviteListItem } from '~/types/api'


const api = useApi()
const uiStore = useUiStore()
const { t: $t } = useI18n()

const createForm = ref({ email: '', role: 'member' })
const createLoading = ref(false)
const invites = ref<InviteListItem[]>([])
const listLoading = ref(false)

function statusClass(status: string): string {
  const map: Record<string, string> = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    used: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    expired: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  }
  return map[status] ?? 'bg-gray-100 text-gray-800'
}

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

interface RawInvite {
  id: string
  email: string
  role: string
  created_at: string
  expires_at: string
  used_at: string | null
}

function toInviteListItem(raw: RawInvite): InviteListItem {
  const now = new Date().toISOString()
  let status: 'active' | 'used' | 'expired' = 'active'
  if (raw.used_at) status = 'used'
  else if (raw.expires_at < now) status = 'expired'
  return { ...raw, status }
}

async function fetchInvites(): Promise<void> {
  listLoading.value = true
  try {
    const list = await api.get<RawInvite[] | { items: RawInvite[] }>(
      '/admin/invites',
    )
    const raw = Array.isArray(list) ? list : (list?.items ?? [])
    invites.value = raw.map(toInviteListItem)
  } catch {
    invites.value = []
  } finally {
    listLoading.value = false
  }
}

async function handleCreateInvite(): Promise<void> {
  createLoading.value = true
  try {
    await api.post('/admin/invites', {
      email: createForm.value.email,
      role: createForm.value.role,
    })
    uiStore.showToast({ type: 'success', message: $t('admin.inviteCreated') })
    createForm.value = { email: '', role: 'member' }
    await fetchInvites()
  } catch (e) {
    uiStore.showToast({
      type: 'error',
      message: e instanceof Error ? e.message : $t('common.error'),
    })
  } finally {
    createLoading.value = false
  }
}

async function handleRevoke(inv: InviteListItem): Promise<void> {
  try {
    await api.del(`/admin/invites/${inv.id}`)
    uiStore.showToast({ type: 'success', message: $t('admin.inviteRevoked') })
    await fetchInvites()
  } catch (e) {
    uiStore.showToast({
      type: 'error',
      message: e instanceof Error ? e.message : $t('common.error'),
    })
  }
}

onMounted(() => {
  fetchInvites()
})
</script>
