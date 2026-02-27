<!--
  @file components/layout/Sidebar.vue
  @brief Desktop navigation sidebar.

  Displays the main navigation links for the authenticated app.
  Collapses based on the UI store's sidebarOpen state. Hidden on
  mobile where BottomNav takes over.
-->
<template>
  <aside
    :class="[
      'hidden md:flex flex-col border-r border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800',
      'transition-all duration-200',
      sidebarOpen ? 'w-64' : 'w-16',
    ]"
    role="navigation"
    :aria-label="$t('a11y.toggleSidebar')"
  >
    <!-- Logo / Brand -->
    <div class="flex h-16 items-center justify-center border-b border-gray-200 px-4 dark:border-gray-700">
      <span v-if="sidebarOpen" class="text-lg font-bold text-primary-600 dark:text-primary-400">
        {{ $t('app.name') }}
      </span>
      <span v-else class="text-lg font-bold text-primary-600 dark:text-primary-400">N</span>
    </div>

    <!-- Navigation links -->
    <nav class="flex-1 space-y-1 p-2">
      <a
        v-for="item in navItems"
        :key="item.path"
        :href="item.path"
        :class="[
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          'hover:bg-gray-100 dark:hover:bg-gray-700',
          'focus:outline-none focus:ring-2 focus:ring-primary-500',
          'text-gray-700 dark:text-gray-200',
        ]"
        :aria-label="item.label"
      >
        <span class="text-lg">{{ item.icon }}</span>
        <span v-if="sidebarOpen">{{ item.label }}</span>
      </a>
    </nav>

    <!-- Sidebar toggle -->
    <div class="border-t border-gray-200 p-2 dark:border-gray-700">
      <button
        class="flex w-full items-center justify-center rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        :aria-label="$t('a11y.toggleSidebar')"
        @click="$emit('toggle')"
      >
        <span>{{ sidebarOpen ? '&laquo;' : '&raquo;' }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * @brief Sidebar component props, events, and navigation items.
 */

defineProps<{
  /** @brief Whether the sidebar is expanded. */
  sidebarOpen: boolean
}>()

defineEmits<{
  (e: 'toggle'): void
}>()

/** @brief Navigation items for the sidebar. */
const navItems = [
  { path: '/app', icon: '📰', label: 'Feed' },
  { path: '/app/events', icon: '📅', label: 'Events' },
  { path: '/app/chat', icon: '💬', label: 'Chat' },
  { path: '/app/media', icon: '🖼️', label: 'Media' },
  { path: '/app/members', icon: '👥', label: 'Members' },
  { path: '/app/settings', icon: '⚙️', label: 'Settings' },
]
</script>
