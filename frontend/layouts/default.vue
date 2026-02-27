<!--
  @file layouts/default.vue
  @brief Authenticated application layout.

  Provides the main app shell with sidebar navigation, top bar,
  and content area. On mobile, the sidebar is hidden and replaced
  by a bottom navigation bar. Toast notifications are rendered
  from the global UI store.
-->
<template>
  <div class="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
    <!-- Skip to content link for accessibility -->
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary-600 focus:px-4 focus:py-2 focus:text-white"
    >
      {{ $t('a11y.skipToContent') }}
    </a>

    <!-- Desktop sidebar -->
    <Sidebar
      :sidebar-open="uiStore.sidebarOpen"
      @toggle="uiStore.toggleSidebar()"
    />

    <!-- Main content area -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <TopBar
        :dark-mode="uiStore.darkMode"
        :user-name="authStore.user?.display_name || ''"
        @toggle-sidebar="uiStore.toggleSidebar()"
        @toggle-dark-mode="uiStore.toggleDarkMode()"
      />

      <main id="main-content" class="flex-1 overflow-y-auto p-4 pb-20 md:p-6 md:pb-6">
        <slot />
      </main>
    </div>

    <!-- Mobile bottom nav -->
    <BottomNav />

    <!-- Toast notifications -->
    <AppToast
      :toasts="uiStore.toasts"
      @dismiss="uiStore.dismissToast"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Default layout setup with store initialization.
 */
import { onMounted } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useUiStore } from '~/stores/ui'
import Sidebar from '~/components/layout/Sidebar.vue'
import TopBar from '~/components/layout/TopBar.vue'
import BottomNav from '~/components/layout/BottomNav.vue'
import AppToast from '~/components/common/AppToast.vue'

const authStore = useAuthStore()
const uiStore = useUiStore()

onMounted(() => {
  uiStore.initDarkMode()
})
</script>
