<!--
  @file pages/app/settings.vue
  @brief Settings parent layout with tab navigation.

  Provides tab navigation (Profile, Account, Security, Notifications)
  and renders child routes via NuxtPage. Active tab is highlighted
  based on the current route path.
-->
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-foreground">
      {{ $t("settings.title") }}
    </h1>

    <!-- Tab navigation -->
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

    <!-- Child route content -->
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Settings layout with tab navigation and child route outlet.
 */
const tabs = [
  { path: "/app/settings/profile", label: "settings.profile" },
  { path: "/app/settings/account", label: "settings.account" },
  { path: "/app/settings/security", label: "settings.security" },
  { path: "/app/settings/notifications", label: "settings.notifications" },
];

const route = useRoute();

/**
 * @brief Check if a tab path matches the current route.
 * @param path - Tab target path.
 * @returns true when the route matches.
 */
function isActive(path: string): boolean {
  return route.path === path;
}
</script>
