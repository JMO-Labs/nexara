<!--
  @file pages/app/settings/index.vue
  @brief Settings index — redirects to profile tab.

  When the user navigates to /app/settings, redirect to
  /app/settings/profile as the default tab.
-->
<script setup lang="ts">
/**
 * @brief Redirect to profile tab as the default settings view.
 *
 * Uses a page-level middleware to redirect before the component
 * initializes, avoiding the SPA suspension that top-level
 * `await navigateTo` causes during client-side navigation.
 */
definePageMeta({
  middleware: [
    function () {
      return navigateTo("/app/settings/profile", { replace: true });
    },
  ],
});
</script>

<template>
  <div />
</template>
