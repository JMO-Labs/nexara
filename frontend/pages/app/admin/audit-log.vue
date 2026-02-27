<!--
  @file pages/app/admin/audit-log.vue
  @brief Admin audit log viewer.

  Paginated table with filter by action type.
  Load more button with cursor pagination. Uses /admin/audit-log API.
-->
<template>
  <div class="space-y-4">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
      <select
        v-model="actionFilter"
        class="max-w-[200px] rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
      >
        <option value="">{{ $t('admin.allActions') }}</option>
        <option value="branding">{{ $t('admin.filterBranding') }}</option>
        <option value="user">{{ $t('admin.users') }}</option>
        <option value="invite">{{ $t('admin.invites') }}</option>
        <option value="settings">{{ $t('admin.settings') }}</option>
      </select>
    </div>

    <AdminAuditLogTable
      :entries="entries"
      :loading="loading"
    />

    <div
      v-if="hasMore && !loading"
      class="flex justify-center"
    >
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        @click="loadMore"
      >
        {{ $t('feed.loadMore') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin audit log page with filter and cursor pagination.
 */
import { ref, watch, onMounted } from 'vue'
import { useApi } from '~/composables/useApi'
import type { AuditLogEntry, AuditLogResponse } from '~/types/api'

const api = useApi()

const entries = ref<AuditLogEntry[]>([])
const loading = ref(false)
const actionFilter = ref('')
const nextCursor = ref<string | null>(null)
const hasMore = ref(false)

async function fetchEntries(append = false): Promise<void> {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('limit', '20')
    if (actionFilter.value) params.set('action', actionFilter.value)
    if (append && nextCursor.value) params.set('cursor', nextCursor.value)
    const res = await api.get<AuditLogResponse>(
      `/admin/audit-log?${params.toString()}`,
    )
    const items = res?.items ?? []
    if (!append) entries.value = items
    else entries.value.push(...items)
    nextCursor.value = res?.next_cursor ?? null
    hasMore.value = res?.has_more ?? false
  } catch {
    if (!append) entries.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}

function loadMore(): void {
  fetchEntries(true)
}

watch(actionFilter, () => {
  nextCursor.value = null
  fetchEntries()
})

onMounted(() => {
  fetchEntries()
})
</script>
