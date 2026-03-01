<!--
  @file components/layout/UserMenu.vue
  @brief Dropdown menu attached to the user avatar in the TopBar.

  Shows user identity, a link to settings, and a logout action.
  Closes on click-outside, Escape, or route navigation.
-->
<template>
  <div ref="menuRef" class="relative">
    <!-- Trigger: avatar button -->
    <button
      class="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
      :aria-label="$t('a11y.userMenu')"
      :aria-expanded="open"
      aria-haspopup="true"
      @click="toggle"
    >
      {{ userInitial }}
    </button>

    <!-- Dropdown panel -->
    <Transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="scale-95 opacity-0"
      enter-to-class="scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="scale-100 opacity-100"
      leave-to-class="scale-95 opacity-0"
    >
      <div
        v-if="open"
        class="absolute right-0 top-full z-50 mt-2 w-56 origin-top-right rounded-lg border border-border bg-popover p-1 shadow-lg"
        role="menu"
        @keydown.escape="close"
      >
        <!-- User identity -->
        <div class="border-b border-border px-3 py-2.5">
          <p class="truncate text-sm font-medium text-foreground">
            {{ displayName }}
          </p>
          <p class="truncate text-xs text-muted-foreground">
            {{ email }}
          </p>
        </div>

        <!-- Settings link -->
        <NuxtLink
          to="/app/settings"
          class="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent"
          role="menuitem"
          @click="close"
        >
          <Cog6ToothIcon class="h-4 w-4 text-muted-foreground" />
          {{ $t("nav.settings") }}
        </NuxtLink>

        <!-- Logout -->
        <button
          class="mt-0.5 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
          role="menuitem"
          @click="handleLogout"
        >
          <ArrowRightStartOnRectangleIcon class="h-4 w-4" />
          {{ $t("nav.logout") }}
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief UserMenu dropdown with click-outside and Escape handling.
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import {
  Cog6ToothIcon,
  ArrowRightStartOnRectangleIcon,
} from "@heroicons/vue/24/outline";
import { useAuthStore } from "~/stores/auth";

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

/** @brief Whether the dropdown is visible. */
const open = ref(false);

/** @brief Template ref for click-outside detection. */
const menuRef = ref<HTMLElement | null>(null);

/** @brief First character of the user's display name for avatar fallback. */
const userInitial = computed(
  () => authStore.user?.display_name?.charAt(0)?.toUpperCase() || "?",
);

/** @brief User display name. */
const displayName = computed(
  () => authStore.user?.display_name || authStore.user?.username || "",
);

/** @brief User email. */
const email = computed(() => authStore.user?.email || "");

function toggle(): void {
  open.value = !open.value;
}

function close(): void {
  open.value = false;
}

async function handleLogout(): Promise<void> {
  close();
  await authStore.logout();
  await router.push("/auth/login");
}

function onClickOutside(event: MouseEvent): void {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    close();
  }
}

watch(() => route.path, close);

onMounted(() => {
  document.addEventListener("mousedown", onClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener("mousedown", onClickOutside);
});
</script>
