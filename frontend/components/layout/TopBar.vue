<!--
  @file components/layout/TopBar.vue
  @brief Top navigation bar with search, notifications, and user menu.

  Displayed at the top of the authenticated app layout. Contains the
  search input, notification bell, dark mode toggle, and user avatar menu.
-->
<template>
  <header class="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-gray-800">
    <!-- Left: Mobile menu + Search -->
    <div class="flex items-center gap-3">
      <button
        class="md:hidden rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        :aria-label="$t('a11y.openMenu')"
        @click="$emit('toggle-sidebar')"
      >
        <span class="text-xl">&#9776;</span>
      </button>
      <div class="relative">
        <input
          type="search"
          :placeholder="$t('common.search')"
          :aria-label="$t('common.search')"
          class="w-48 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white lg:w-80"
        />
      </div>
    </div>

    <!-- Right: Actions -->
    <div class="flex items-center gap-2">
      <!-- Dark mode toggle -->
      <button
        class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        :aria-label="$t('a11y.toggleDarkMode')"
        @click="$emit('toggle-dark-mode')"
      >
        <span v-if="darkMode">&#9788;</span>
        <span v-else>&#9790;</span>
      </button>

      <!-- Notifications -->
      <button
        class="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        :aria-label="$t('a11y.notifications')"
      >
        <span class="text-lg">&#128276;</span>
      </button>

      <!-- User menu -->
      <button
        class="flex items-center gap-2 rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-700"
        :aria-label="$t('a11y.userMenu')"
      >
        <div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700 dark:bg-primary-900 dark:text-primary-300">
          {{ userInitial }}
        </div>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * @brief TopBar component props and events.
 */
import { computed } from 'vue'

const props = defineProps<{
  /** @brief Whether dark mode is currently active. */
  darkMode: boolean
  /** @brief Display name of the current user. */
  userName: string
}>()

defineEmits<{
  (e: 'toggle-sidebar'): void
  (e: 'toggle-dark-mode'): void
}>()

/** @brief First character of the user's display name for avatar fallback. */
const userInitial = computed(() => props.userName?.charAt(0)?.toUpperCase() || '?')
</script>
