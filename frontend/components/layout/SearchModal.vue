<!--
  @file components/layout/SearchModal.vue
  @brief SuperSearch command palette modal (Cmd+K / Ctrl+K).

  Provides a centered overlay dialog with a search input, keyboard
  navigation, and live API-backed search results for posts, comments,
  users, and events. Shows quick-action page links when the input is
  empty. Closes on Escape, click-outside, or route navigation.
-->
<template>
  <Teleport to="body">
    <Transition name="search-modal">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      >
        <!-- Backdrop — click anywhere on it to dismiss -->
        <div
          class="fixed inset-0 bg-background/80 backdrop-blur-sm"
          aria-hidden="true"
          @click="close"
        />

        <!-- Dialog -->
        <div
          ref="dialogRef"
          role="dialog"
          aria-modal="true"
          :aria-label="$t('search.placeholder')"
          class="relative z-10 w-full max-w-lg overflow-hidden rounded-lg border border-border bg-popover shadow-lg"
        >
          <!-- Search input -->
          <div class="flex items-center border-b border-border px-3">
            <MagnifyingGlassIcon
              class="mr-2 h-4 w-4 shrink-0 text-muted-foreground"
            />
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              :placeholder="$t('search.placeholder')"
              class="flex h-11 w-full bg-transparent py-3 text-sm text-foreground outline-none placeholder:text-muted-foreground"
              @keydown.down.prevent="navigateDown"
              @keydown.up.prevent="navigateUp"
              @keydown.enter.prevent="selectActive"
            />
            <kbd
              class="ml-2 hidden sm:inline-flex h-5 items-center rounded border border-border bg-muted px-1 font-mono text-[10px] text-muted-foreground"
            >
              ESC
            </kbd>
          </div>

          <!-- Results area -->
          <div class="max-h-72 overflow-y-auto p-2">
            <!-- API search results -->
            <template v-if="query.trim().length >= 2">
              <div
                v-if="loading"
                class="py-6 text-center text-sm text-muted-foreground"
              >
                {{ $t("common.loading") }}
              </div>
              <p
                v-else-if="displayItems.length === 0"
                class="py-6 text-center text-sm text-muted-foreground"
              >
                {{ $t("search.noResults") }}
              </p>
              <div v-else>
                <button
                  v-for="(item, idx) in displayItems"
                  :key="`${item.type}-${item.id}`"
                  :class="[
                    'flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors text-left',
                    idx === activeIndex
                      ? 'bg-accent text-accent-foreground'
                      : 'text-popover-foreground hover:bg-accent/50',
                  ]"
                  @mouseenter="activeIndex = idx"
                  @click="navigateToResult(item)"
                >
                  <component
                    :is="typeIcon(item.type)"
                    class="h-4 w-4 shrink-0 text-muted-foreground"
                  />
                  <div class="min-w-0 flex-1">
                    <p class="truncate font-medium">{{ item.title }}</p>
                    <p
                      v-if="item.snippet && item.snippet !== item.title"
                      class="truncate text-xs text-muted-foreground"
                    >
                      {{ item.snippet }}
                    </p>
                  </div>
                  <span
                    class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground"
                  >
                    {{ $t(typeToI18nKey(item.type)) }}
                  </span>
                </button>

                <!-- Link to full search page -->
                <button
                  :class="[
                    'flex w-full items-center justify-center gap-2 rounded-md px-2 py-2 text-sm transition-colors mt-1',
                    displayItems.length === activeIndex
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent/50',
                  ]"
                  @mouseenter="activeIndex = displayItems.length"
                  @click="goToFullSearch"
                >
                  {{ $t("search.loadMore") }}
                </button>
              </div>
            </template>

            <!-- Quick actions for short/empty query -->
            <template v-else>
              <p
                v-if="query.trim().length > 0 && query.trim().length < 2"
                class="py-6 text-center text-sm text-muted-foreground"
              >
                {{ $t("search.noResults") }}
              </p>
              <template v-else>
                <p
                  class="px-2 py-1.5 text-xs font-semibold text-muted-foreground"
                >
                  {{ $t("search.hint") }}
                </p>
                <button
                  v-for="(item, idx) in quickActions"
                  :key="item.id"
                  :class="[
                    'flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors',
                    idx === activeIndex
                      ? 'bg-accent text-accent-foreground'
                      : 'text-popover-foreground hover:bg-accent/50',
                  ]"
                  @mouseenter="activeIndex = idx"
                  @click="navigateToPage(item)"
                >
                  <component
                    :is="item.icon"
                    class="h-4 w-4 shrink-0 text-muted-foreground"
                  />
                  <span>{{ $t(item.labelKey) }}</span>
                </button>
              </template>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief SearchModal logic: debounced API search, keyboard shortcuts,
 * keyboard navigation, quick actions, and route-based closing.
 */
import { ref, computed, watch, nextTick, type Component } from "vue";
import { useMagicKeys, watchDebounced } from "@vueuse/core";
import {
  MagnifyingGlassIcon,
  NewspaperIcon,
  CalendarDaysIcon,
  ChatBubbleLeftRightIcon,
  UserGroupIcon,
  ChatBubbleBottomCenterTextIcon,
} from "@heroicons/vue/24/outline";
import { useApi } from "~/composables/useApi";
import type { SearchResponse, SearchResultItem } from "~/types/api";

interface QuickAction {
  id: string;
  labelKey: string;
  icon: Component;
  path: string;
}

const api = useApi();

const open = defineModel<boolean>("open", { default: false });

const query = ref("");
const activeIndex = ref(0);
const loading = ref(false);
const searchData = ref<SearchResponse | null>(null);
const inputRef = ref<HTMLInputElement | null>(null);
const dialogRef = ref<HTMLElement | null>(null);

/** @brief Quick-access navigation items shown when search input is empty. */
const quickActions: QuickAction[] = [
  {
    id: "feed",
    labelKey: "nav.feed",
    icon: NewspaperIcon,
    path: "/app",
  },
  {
    id: "events",
    labelKey: "nav.events",
    icon: CalendarDaysIcon,
    path: "/app/events",
  },
  {
    id: "chat",
    labelKey: "nav.chat",
    icon: ChatBubbleLeftRightIcon,
    path: "/app/chat",
  },
  {
    id: "members",
    labelKey: "nav.members",
    icon: UserGroupIcon,
    path: "/app/members",
  },
];

/**
 * @brief Flat list of search result items from all content types.
 *
 * Ordered: posts, comments, users, events (most relevant first).
 */
const displayItems = computed((): SearchResultItem[] => {
  if (!searchData.value) return [];
  const items: SearchResultItem[] = [];
  for (const t of ["posts", "comments", "users", "events"]) {
    const r = searchData.value.results[t];
    if (r) items.push(...r.items);
  }
  return items.slice(0, 8);
});

/** @brief Map content type to an icon component. */
function typeIcon(type: string): Component {
  const map: Record<string, Component> = {
    posts: NewspaperIcon,
    comments: ChatBubbleBottomCenterTextIcon,
    users: UserGroupIcon,
    events: CalendarDaysIcon,
  };
  return map[type] ?? MagnifyingGlassIcon;
}

/** @brief Map content type to i18n key for display label. */
function typeToI18nKey(type: string): string {
  const map: Record<string, string> = {
    posts: "search.posts",
    comments: "search.comments",
    users: "search.people",
    events: "search.events",
  };
  return map[type] ?? `search.${type}`;
}

/** @brief Navigate to a search result item. */
function navigateToResult(item: SearchResultItem): void {
  let path = "#";
  if (item.type === "posts") path = `/app/post/${item.id}`;
  else if (item.type === "comments" && item.parent_id)
    path = `/app/post/${item.parent_id}`;
  router.push(path);
  close();
}

/** @brief Navigate to a quick-action page link. */
function navigateToPage(item: QuickAction): void {
  router.push(item.path);
  close();
}

/** @brief Navigate to the full search results page. */
function goToFullSearch(): void {
  router.push({ path: "/app/search", query: { q: query.value.trim() } });
  close();
}

/** @brief Total count of navigable items for keyboard nav. */
const totalItems = computed(() => {
  if (query.value.trim().length >= 2) {
    return displayItems.value.length > 0 ? displayItems.value.length + 1 : 0;
  }
  return query.value.trim().length === 0 ? quickActions.length : 0;
});

function navigateDown(): void {
  if (activeIndex.value < totalItems.value - 1) activeIndex.value++;
}

function navigateUp(): void {
  if (activeIndex.value > 0) activeIndex.value--;
}

const router = useRouter();

function selectActive(): void {
  if (query.value.trim().length >= 2) {
    if (activeIndex.value === displayItems.value.length) {
      goToFullSearch();
    } else {
      const item = displayItems.value[activeIndex.value];
      if (item) navigateToResult(item);
    }
  } else if (query.value.trim().length === 0) {
    const item = quickActions[activeIndex.value];
    if (item) navigateToPage(item);
  }
}

function close(): void {
  open.value = false;
}

/** @brief Fetch search results from the backend API. */
async function fetchSearch(): Promise<void> {
  const q = query.value.trim();
  if (q.length < 2) {
    searchData.value = null;
    return;
  }
  loading.value = true;
  try {
    const params = new URLSearchParams({
      q,
      types: "posts,users,events,comments",
      limit: "8",
    });
    searchData.value = await api.get<SearchResponse>(`/search?${params}`);
  } catch {
    searchData.value = null;
  } finally {
    loading.value = false;
  }
}

/** @brief Debounced watch on query to avoid excessive API calls (300ms). */
watchDebounced(query, fetchSearch, { debounce: 300 });

/** @brief Reset query and state when the modal opens; auto-focus input. */
watch(open, async (isOpen) => {
  if (isOpen) {
    query.value = "";
    activeIndex.value = 0;
    searchData.value = null;
    await nextTick();
    inputRef.value?.focus();
  }
});

/** @brief Reset activeIndex when results change. */
watch([query, displayItems], () => {
  activeIndex.value = 0;
});

/** @brief Cmd+K / Ctrl+K global shortcut to toggle the modal. */
const keys = useMagicKeys({
  passive: false,
  onEventFired(e) {
    if (e.key === "k" && (e.metaKey || e.ctrlKey)) e.preventDefault();
    if (e.key === "Escape" && e.type === "keydown" && open.value) {
      e.preventDefault();
      close();
    }
  },
});
watch([keys["Meta_K"], keys["Ctrl_K"]], ([meta, ctrl]) => {
  if (meta || ctrl) open.value = !open.value;
});

/** @brief Close modal on route change. */
watch(
  () => router.currentRoute.value.path,
  () => {
    if (open.value) close();
  },
);
</script>

<style scoped>
.search-modal-enter-active,
.search-modal-leave-active {
  transition:
    opacity 150ms ease,
    transform 150ms ease;
}

.search-modal-enter-from,
.search-modal-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
