<!--
  @file layouts/public.vue
  @brief Public layout for landing and auth pages.

  Minimal layout without sidebar or top bar. Provides a centered
  content area suitable for login, registration, and the landing page.
-->
<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <slot />
  </div>
</template>
