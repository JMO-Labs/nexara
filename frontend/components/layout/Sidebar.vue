<!--
  @file components/layout/Sidebar.vue
  @brief Minimal icon-rail sidebar for desktop navigation.

  Always-collapsed vertical rail (w-14) with Heroicon nav items and
  CSS tooltips on hover. Hidden on mobile where BottomNav takes over.
  Uses NuxtLink for SPA routing with active-route highlighting.
-->
<template>
  <aside
    class="hidden md:flex flex-col w-14 border-r border-border bg-background"
    role="navigation"
    :aria-label="$t('a11y.toggleSidebar')"
  >
    <!-- Logo -->
    <div class="flex h-14 items-center justify-center border-b border-border">
      <span class="text-lg font-bold text-primary">N</span>
    </div>

    <!-- Navigation links -->
    <nav class="flex flex-1 flex-col items-center gap-1 py-3">
      <NuxtLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item group relative flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        :class="{ 'bg-accent text-accent-foreground': isActive(item.path) }"
        :aria-label="item.labelKey ? $t(item.labelKey) : item.label"
      >
        <component :is="item.icon" class="h-5 w-5" />

        <!-- CSS tooltip -->
        <span
          class="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-md bg-popover px-2 py-1 text-xs font-medium text-popover-foreground shadow-md opacity-0 transition-opacity group-hover:opacity-100"
        >
          {{ item.labelKey ? $t(item.labelKey) : item.label }}
        </span>
      </NuxtLink>
    </nav>

    <!-- Bottom section: Settings -->
    <div class="flex flex-col items-center gap-1 border-t border-border py-3">
      <NuxtLink
        to="/app/settings"
        class="nav-item group relative flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        :class="{ 'bg-accent text-accent-foreground': isActive('/app/settings') }"
        :aria-label="$t('nav.settings')"
      >
        <Cog6ToothIcon class="h-5 w-5" />
        <span
          class="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-md bg-popover px-2 py-1 text-xs font-medium text-popover-foreground shadow-md opacity-0 transition-opacity group-hover:opacity-100"
        >
          {{ $t('nav.settings') }}
        </span>
      </NuxtLink>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * @brief Sidebar icon-rail with Heroicons and route-aware highlighting.
 */
import {
  NewspaperIcon,
  CalendarDaysIcon,
  ChatBubbleLeftRightIcon,
  PhotoIcon,
  UserGroupIcon,
  Cog6ToothIcon,
  ShieldCheckIcon,
} from '@heroicons/vue/24/outline'
import { useAuthStore } from '~/stores/auth'
import { computed } from 'vue'

const authStore = useAuthStore()

/** @brief Primary navigation items rendered in the rail. */
const navItems = computed(() => {
  const items: Array<{ path: string; icon: typeof NewspaperIcon; label: string; labelKey?: string }> = [
    { path: '/app', icon: NewspaperIcon, label: 'Feed', labelKey: 'nav.feed' },
    { path: '/app/events', icon: CalendarDaysIcon, label: 'Events', labelKey: 'nav.events' },
    { path: '/app/chat', icon: ChatBubbleLeftRightIcon, label: 'Chat', labelKey: 'nav.chat' },
    { path: '/app/media', icon: PhotoIcon, label: 'Media', labelKey: 'nav.media' },
    { path: '/app/members', icon: UserGroupIcon, label: 'Members', labelKey: 'nav.members' },
  ]
  if (authStore.user?.role === 'admin') {
    items.push({ path: '/app/admin', icon: ShieldCheckIcon, label: 'Admin', labelKey: 'nav.admin' })
  }
  return items
})

const route = useRoute()

/**
 * @brief Determine if a nav item matches the current route.
 * @param path - The nav item's target path.
 * @returns true when the route exactly matches or starts with the path.
 */
function isActive(path: string): boolean {
  if (path === '/app') return route.path === '/app'
  return route.path.startsWith(path)
}
</script>
