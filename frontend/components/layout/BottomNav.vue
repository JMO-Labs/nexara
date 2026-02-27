<!--
  @file components/layout/BottomNav.vue
  @brief Mobile bottom navigation bar with Heroicons.

  Fixed at the bottom on mobile screens (md:hidden). Provides quick
  access to the main navigation items using NuxtLink for SPA routing.
-->
<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-border bg-background py-1.5 md:hidden"
    role="navigation"
    :aria-label="$t('a11y.openMenu')"
  >
    <NuxtLink
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      class="flex flex-col items-center gap-0.5 rounded-md px-3 py-1 transition-colors"
      :class="isActive(item.path)
        ? 'text-primary'
        : 'text-muted-foreground hover:text-foreground'"
      :aria-label="$t(item.labelKey)"
    >
      <component :is="item.icon" class="h-5 w-5" />
      <span class="text-[10px] font-medium">{{ $t(item.labelKey) }}</span>
    </NuxtLink>
  </nav>
</template>

<script setup lang="ts">
/**
 * @brief BottomNav component with Heroicons and route-aware highlighting.
 */
import {
  NewspaperIcon,
  CalendarDaysIcon,
  ChatBubbleLeftRightIcon,
  PhotoIcon,
  EllipsisHorizontalIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()

/** @brief Navigation items for the compact bottom bar. */
const navItems = [
  { path: '/app', icon: NewspaperIcon, labelKey: 'nav.feed' },
  { path: '/app/events', icon: CalendarDaysIcon, labelKey: 'nav.events' },
  { path: '/app/chat', icon: ChatBubbleLeftRightIcon, labelKey: 'nav.chat' },
  { path: '/app/media', icon: PhotoIcon, labelKey: 'nav.media' },
  { path: '/app/settings', icon: EllipsisHorizontalIcon, labelKey: 'nav.more' },
]

/**
 * @brief Determine if a nav item matches the current route.
 * @param path - The nav item's target path.
 */
function isActive(path: string): boolean {
  if (path === '/app') return route.path === '/app'
  return route.path.startsWith(path)
}
</script>
