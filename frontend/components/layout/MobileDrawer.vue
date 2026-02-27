<!--
  @file components/layout/MobileDrawer.vue
  @brief Slide-out navigation drawer for mobile screens.

  Opens from the left when the mobile hamburger is tapped. Contains
  the same nav items as the desktop sidebar rail, plus the app branding.
  Closes on click-outside, Escape, or route navigation.
-->
<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div
        v-if="open"
        class="fixed inset-0 z-50 md:hidden"
        @keydown.escape="$emit('close')"
      >
        <!-- Backdrop -->
        <div
          class="fixed inset-0 bg-background/80 backdrop-blur-sm"
          aria-hidden="true"
          @click="$emit('close')"
        />

        <!-- Drawer panel -->
        <nav
          class="fixed inset-y-0 left-0 z-10 flex w-64 flex-col border-r border-border bg-background shadow-lg"
          role="navigation"
          :aria-label="$t('a11y.openMenu')"
        >
          <!-- Header -->
          <div class="flex h-14 items-center border-b border-border px-4">
            <span class="text-lg font-bold text-primary">{{ $t('app.name') }}</span>
          </div>

          <!-- Nav links -->
          <div class="flex-1 overflow-y-auto p-3 space-y-1">
            <NuxtLink
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
              @click="$emit('close')"
            >
              <component :is="item.icon" class="h-5 w-5 text-muted-foreground" />
              {{ $t(item.labelKey) }}
            </NuxtLink>
          </div>
        </nav>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief MobileDrawer props, events, and navigation items.
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

defineProps<{
  /** @brief Whether the drawer is currently visible. */
  open: boolean
}>()

defineEmits<{
  (e: 'close'): void
}>()

/** @brief Navigation items shown in the mobile drawer. */
const navItems = computed(() => {
  const items = [
    { path: '/app', icon: NewspaperIcon, labelKey: 'nav.feed' },
    { path: '/app/events', icon: CalendarDaysIcon, labelKey: 'nav.events' },
    { path: '/app/chat', icon: ChatBubbleLeftRightIcon, labelKey: 'nav.chat' },
    { path: '/app/media', icon: PhotoIcon, labelKey: 'nav.media' },
    { path: '/app/members', icon: UserGroupIcon, labelKey: 'nav.members' },
    { path: '/app/settings', icon: Cog6ToothIcon, labelKey: 'nav.settings' },
  ]
  if (authStore.user?.role === 'admin') {
    items.splice(-1, 0, { path: '/app/admin', icon: ShieldCheckIcon, labelKey: 'nav.admin' })
  }
  return items
})
</script>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 200ms ease;
}
.drawer-enter-active nav,
.drawer-leave-active nav {
  transition: transform 200ms ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from nav,
.drawer-leave-to nav {
  transform: translateX(-100%);
}
</style>
