<!--
  @file layouts/public.vue
  @brief Public layout for landing and auth pages.

  Minimal layout without sidebar or top bar. Provides a centered
  content area suitable for login, registration, and the landing page.
-->
<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <slot />
    <!-- Toast notifications (Teleported to body by AppToast) -->
    <AppToast :toasts="uiStore.toasts" @dismiss="uiStore.dismissToast" />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Public layout setup. Initializes dark mode on mount for SSR-safe
 * system preference detection on the landing page and auth pages.
 */
import { onMounted } from "vue";
import { useUiStore } from "~/stores/ui";
import AppToast from "~/components/common/AppToast.vue";

const uiStore = useUiStore();

onMounted(() => {
  uiStore.initDarkMode();
});
</script>
