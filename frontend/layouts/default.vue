<!--
  @file layouts/default.vue
  @brief Authenticated application layout with flexible 3-column grid.

  Structure: icon-rail sidebar | main area (TopBar + content grid) | calendar bar.
  The content grid splits into a fluid feed column and a sticky
  calendar sidebar on lg+ screens. The calendar is hidden on
  settings / admin routes. Mobile uses a bottom nav instead.
-->
<template>
  <div class="flex h-screen overflow-hidden bg-background">
    <!-- Skip to content link for accessibility -->
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
    >
      {{ $t("a11y.skipToContent") }}
    </a>

    <!-- Desktop sidebar rail -->
    <Sidebar />

    <!-- Main content area -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <div class="relative">
        <TopBar
          :dark-mode="uiStore.darkMode"
          @toggle-mobile-nav="mobileNavOpen = !mobileNavOpen"
          @toggle-dark-mode="uiStore.toggleDarkMode()"
          @open-search="uiStore.openSearch()"
          @toggle-notifications="notifPanelOpen = !notifPanelOpen"
        />
        <NotificationPanel
          :open="notifPanelOpen"
          @close="notifPanelOpen = false"
        />
      </div>

      <main id="main-content" class="flex-1 overflow-y-auto">
        <div class="flex gap-6 p-4 pb-20 md:p-6 md:pb-6">
          <!-- Page content column — width adapts by route (wider for settings/admin) -->
          <div class="min-w-0 flex-1">
            <div class="mx-auto" :class="contentMaxWidth">
              <slot />
            </div>
          </div>

          <!-- Calendar sidebar pinned to right edge (desktop only, hidden on settings/admin) -->
          <CalendarSidebar v-if="showCalendar" />
        </div>
      </main>
    </div>

    <!-- Mobile bottom nav -->
    <BottomNav />

    <!-- Mobile nav overlay -->
    <MobileDrawer :open="mobileNavOpen" @close="mobileNavOpen = false" />

    <!-- Search modal -->
    <SearchModal v-model:open="uiStore.searchOpen" />

    <!-- Toast notifications (Teleported to body by AppToast) -->
    <AppToast :toasts="uiStore.toasts" @dismiss="uiStore.dismissToast" />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Default layout setup with store initialization.
 */
import { ref, computed, watch, onMounted } from "vue";
import { useAuthStore } from "~/stores/auth";
import { useUiStore } from "~/stores/ui";
import { useFeedStore } from "~/stores/feed";
import { useNotificationsStore } from "~/stores/notifications";
import { useBranding } from "~/composables/useBranding";
import { useSSE } from "~/composables/useSSE";
import { useEventBus } from "~/composables/useEventBus";
import Sidebar from "~/components/layout/Sidebar.vue";
import TopBar from "~/components/layout/TopBar.vue";
import BottomNav from "~/components/layout/BottomNav.vue";
import CalendarSidebar from "~/components/layout/CalendarSidebar.vue";
import SearchModal from "~/components/layout/SearchModal.vue";
import MobileDrawer from "~/components/layout/MobileDrawer.vue";
import AppToast from "~/components/common/AppToast.vue";
import NotificationPanel from "~/components/notifications/NotificationPanel.vue";

const authStore = useAuthStore();
const uiStore = useUiStore();
useFeedStore();
useNotificationsStore();
const { fetchBranding } = useBranding();
const route = useRoute();
const { dispatch } = useEventBus();

const { connect: sseConnect, disconnect: sseDisconnect } = useSSE(
  (type, data) => dispatch(type, data),
);

/** @brief Whether the mobile navigation drawer is open. */
const mobileNavOpen = ref(false);

/** @brief Whether the notification dropdown panel is visible. */
const notifPanelOpen = ref(false);

/** @brief Routes where the calendar sidebar should be hidden. */
const showCalendar = computed(() => {
  return (
    !route.path.startsWith("/app/settings") &&
    !route.path.startsWith("/app/admin")
  );
});

/** @brief Max-width class — wider for settings and admin pages, narrow for feed. */
const contentMaxWidth = computed(() => {
  if (
    route.path.startsWith("/app/settings") ||
    route.path.startsWith("/app/admin")
  ) {
    return "max-w-4xl";
  }
  return "max-w-2xl";
});

/**
 * @brief Connect or disconnect SSE whenever auth state changes.
 *
 * Handles both the initial page load (where the auth middleware may
 * restore the session asynchronously via refresh cookie) and
 * subsequent login/logout transitions within the SPA.
 */
watch(
  () => authStore.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      sseConnect();
    } else {
      sseDisconnect();
    }
  },
);

onMounted(() => {
  uiStore.initDarkMode();
  fetchBranding();
  if (authStore.isAuthenticated) {
    sseConnect();
  }
});
</script>
