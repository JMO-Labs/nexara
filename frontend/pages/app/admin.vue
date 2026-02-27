<!--
  @file pages/app/admin.vue
  @brief Admin panel layout with tab navigation.

  Requires admin role; redirects non-admins to /app.
  Tabs: Dashboard, Users, Invites, Settings, Audit Log.
-->
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-foreground">
      {{ $t('nav.admin') }}
    </h1>

    <ul
      class="flex flex-wrap gap-1 border-b border-border text-sm font-medium text-muted-foreground"
      role="tablist"
    >
      <li v-for="tab in tabs" :key="tab.path">
        <NuxtLink
          :to="tab.path"
          class="inline-block rounded-t-lg border-b-2 border-transparent px-4 py-3 transition-colors hover:border-muted-foreground hover:text-foreground"
          :class="{
            'border-primary text-foreground': isActive(tab.path),
          }"
          role="tab"
        >
          {{ $t(tab.label) }}
        </NuxtLink>
      </li>
    </ul>

    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin layout with tab navigation.
 *
 * Role-based access is enforced by the global auth middleware;
 * no additional client-side guard needed here.
 */
const route = useRoute()

const tabs = [
  { path: '/app/admin', label: 'admin.dashboard' },
  { path: '/app/admin/users', label: 'admin.users' },
  { path: '/app/admin/invites', label: 'admin.invites' },
  { path: '/app/admin/settings', label: 'admin.settings' },
  { path: '/app/admin/audit-log', label: 'admin.audit_log' },
]

function isActive(path: string): boolean {
  if (path === '/app/admin') return route.path === '/app/admin'
  return route.path.startsWith(path)
}
</script>
