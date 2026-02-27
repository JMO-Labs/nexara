<!--
  @file components/layout/BottomNav.vue
  @brief Mobile bottom navigation bar.

  Displayed on mobile screens (md:hidden) as a fixed bottom bar.
  Provides quick access to the main navigation items.
-->
<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-gray-200 bg-white py-2 md:hidden dark:border-gray-700 dark:bg-gray-800"
    role="navigation"
    :aria-label="$t('a11y.openMenu')"
  >
    <a
      v-for="item in navItems"
      :key="item.path"
      :href="item.path"
      class="flex flex-col items-center gap-0.5 rounded-lg px-3 py-1 text-gray-500 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400"
      :aria-label="item.label"
    >
      <span class="text-xl">{{ item.icon }}</span>
      <span class="text-xs">{{ item.label }}</span>
    </a>
  </nav>
</template>

<script setup lang="ts">
/**
 * @brief BottomNav component with navigation items.
 */

/** @brief Subset of navigation items for the compact bottom bar. */
const navItems = [
  { path: '/app', icon: '📰', label: 'Feed' },
  { path: '/app/events', icon: '📅', label: 'Events' },
  { path: '/app/chat', icon: '💬', label: 'Chat' },
  { path: '/app/media', icon: '🖼️', label: 'Media' },
  { path: '/app/settings', icon: '⚙️', label: 'More' },
]
</script>
