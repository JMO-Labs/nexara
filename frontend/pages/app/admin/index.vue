<!--
  @file pages/app/admin/index.vue
  @brief Admin dashboard with metrics and recent audit log.

  Grid of MetricsCard components, recent audit entries, WAF blocks summary.
  Fetches from /admin/metrics and /admin/audit-log?limit=5.
-->
<template>
  <div class="space-y-6">
    <div
      v-if="authStore.user?.role !== 'admin'"
      class="rounded-lg border border-border bg-card p-6 text-center text-muted-foreground"
    >
      {{ $t('common.loading') }}
    </div>

    <template v-else>
      <!-- Metrics grid -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <AdminMetricsCard
          :title="$t('admin.total_users')"
          :value="metrics?.total_users ?? 0"
        />
        <AdminMetricsCard
          :title="$t('admin.active_users')"
          :value="metrics?.active_users_30d ?? 0"
        />
        <AdminMetricsCard
          :title="$t('admin.online_now')"
          :value="metrics?.online_now ?? 0"
        />
        <AdminMetricsCard
          :title="$t('admin.total_posts')"
          :value="metrics?.total_posts ?? 0"
        />
        <AdminMetricsCard
          :title="$t('admin.posts_7d')"
          :value="metrics?.posts_7d ?? 0"
        />
        <AdminMetricsCard
          :title="$t('admin.media_files')"
          :value="metrics?.media_files ?? 0"
        />
        <AdminMetricsCard
          :title="$t('admin.storage_used')"
          :value="storageFormatted"
        />
        <AdminMetricsCard
          v-if="metrics?.waf_blocks_total !== undefined"
          :title="$t('admin.waf_blocks')"
          :value="metrics.waf_blocks_total"
        />
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- Recent audit log -->
        <div class="rounded-lg border border-border bg-card p-4">
          <h2 class="mb-4 text-lg font-semibold text-foreground">
            {{ $t('admin.recent_audit') }}
          </h2>
          <AdminAuditLogTable
            :entries="auditEntries"
            :loading="auditLoading"
          />
        </div>

        <!-- WAF blocks summary -->
        <div
          v-if="metrics?.waf_blocks_total !== undefined"
          class="rounded-lg border border-border bg-card p-4"
        >
          <h2 class="mb-4 text-lg font-semibold text-foreground">
            {{ $t('admin.waf_blocks') }}
          </h2>
          <p class="text-2xl font-bold text-foreground">
            {{ metrics.waf_blocks_total?.toLocaleString() ?? 0 }}
          </p>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ $t('admin.wafBlocksPeriod') }}
          </p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin dashboard with metrics and audit log.
 */
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useApi } from '~/composables/useApi'
import type { AdminMetricsResponse, AuditLogEntry } from '~/types/api'

const authStore = useAuthStore()
const api = useApi()

const metrics = ref<AdminMetricsResponse | null>(null)
const auditEntries = ref<AuditLogEntry[]>([])
const auditLoading = ref(false)

const storageFormatted = computed(() => {
  const bytes = metrics.value?.storage_used_bytes ?? 0
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
})

async function fetchMetrics(): Promise<void> {
  try {
    metrics.value = await api.get<AdminMetricsResponse>('/admin/metrics')
  } catch {
    metrics.value = null
  }
}

async function fetchAuditLog(): Promise<void> {
  auditLoading.value = true
  try {
    const res = await api.get<{ items: AuditLogEntry[] }>(
      '/admin/audit-log?limit=5',
    )
    auditEntries.value = res?.items ?? []
  } catch {
    auditEntries.value = []
  } finally {
    auditLoading.value = false
  }
}

onMounted(async () => {
  if (authStore.user?.role === 'admin') {
    await Promise.all([fetchMetrics(), fetchAuditLog()])
  }
})
</script>
