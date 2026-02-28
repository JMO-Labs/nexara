<!--
  @file components/layout/TopBar.vue
  @brief Top navigation bar with centered search trigger and action icons.

  The search input is a styled button that opens the SuperSearch modal.
  Dark mode, notifications, and user avatar sit on the right.
  Mobile hamburger remains on the left for the slide-out drawer.
-->
<template>
  <header
    class="flex h-14 items-center gap-4 border-b border-border bg-background px-4"
  >
    <!-- Left: Mobile menu toggle -->
    <button
      class="md:hidden flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
      :aria-label="$t('a11y.openMenu')"
      @click="$emit('toggle-mobile-nav')"
    >
      <Bars3Icon class="h-5 w-5" />
    </button>

    <!-- Center: Search trigger button -->
    <button
      class="mx-auto flex h-9 w-full max-w-md items-center gap-2 rounded-md border border-input bg-muted/50 px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      @click="$emit('open-search')"
    >
      <MagnifyingGlassIcon class="h-4 w-4 shrink-0" />
      <span class="flex-1 text-left">{{ $t("common.search") }}</span>
      <kbd
        class="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground"
      >
        <span class="text-xs">&#8984;</span>K
      </kbd>
    </button>

    <!-- Right: Actions -->
    <div class="flex items-center gap-1">
      <!-- Dark mode toggle -->
      <button
        class="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        :aria-label="$t('a11y.toggleDarkMode')"
        @click="$emit('toggle-dark-mode')"
      >
        <SunIcon v-if="darkMode" class="h-5 w-5" />
        <MoonIcon v-else class="h-5 w-5" />
      </button>

      <!-- Notifications -->
      <NotificationBell @toggle="$emit('toggle-notifications')" />

      <!-- User menu dropdown -->
      <UserMenu />
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * @brief TopBar component props and events.
 */
import {
  Bars3Icon,
  MagnifyingGlassIcon,
  SunIcon,
  MoonIcon,
} from "@heroicons/vue/24/outline";
import NotificationBell from "~/components/notifications/NotificationBell.vue";
import UserMenu from "~/components/layout/UserMenu.vue";

defineProps<{
  /** @brief Whether dark mode is currently active. */
  darkMode: boolean;
}>();

defineEmits<{
  "toggle-mobile-nav": [];
  "toggle-dark-mode": [];
  "open-search": [];
  "toggle-notifications": [];
}>();
</script>
