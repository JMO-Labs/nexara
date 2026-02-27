<!--
  @file components/layout/SearchModal.vue
  @brief SuperSearch command palette modal (Cmd+K / Ctrl+K).

  Provides a centered overlay dialog with a search input, keyboard
  navigation for results, and stub sections (Recent, Posts, Members,
  Events). Closes on Escape, click-outside, or route navigation.
-->
<template>
  <Teleport to="body">
    <Transition name="search-modal">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
        @click.self="close"
        @keydown.escape="close"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-background/80 backdrop-blur-sm" aria-hidden="true" />

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
            <MagnifyingGlassIcon class="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
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
            <template v-if="query.trim()">
              <p
                v-if="filteredResults.length === 0"
                class="py-6 text-center text-sm text-muted-foreground"
              >
                {{ $t('search.noResults') }}
              </p>
              <div v-else>
                <div
                  v-for="(group, gi) in groupedResults"
                  :key="group.label"
                  class="mb-2"
                >
                  <p class="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                    {{ group.label }}
                  </p>
                  <button
                    v-for="(item, ii) in group.items"
                    :key="item.id"
                    :class="[
                      'flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors',
                      flatIndex(gi, ii) === activeIndex
                        ? 'bg-accent text-accent-foreground'
                        : 'text-popover-foreground hover:bg-accent/50',
                    ]"
                    @mouseenter="activeIndex = flatIndex(gi, ii)"
                    @click="navigateTo(item)"
                  >
                    <component :is="item.icon" class="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>{{ item.label }}</span>
                  </button>
                </div>
              </div>
            </template>

            <!-- Empty state: quick actions -->
            <template v-else>
              <p class="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                {{ $t('search.hint') }}
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
                @click="navigateTo(item)"
              >
                <component :is="item.icon" class="h-4 w-4 shrink-0 text-muted-foreground" />
                <span>{{ item.label }}</span>
              </button>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * @brief SearchModal logic: keyboard shortcuts, result filtering,
 * keyboard navigation, and route-based closing.
 */
import { ref, computed, watch, nextTick, type Component } from 'vue'
import { useMagicKeys } from '@vueuse/core'
import {
  MagnifyingGlassIcon,
  NewspaperIcon,
  CalendarDaysIcon,
  ChatBubbleLeftRightIcon,
  UserGroupIcon,
} from '@heroicons/vue/24/outline'

interface SearchItem {
  id: string
  label: string
  icon: Component
  path: string
  group: string
}

const open = defineModel<boolean>('open', { default: false })

const query = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)
const dialogRef = ref<HTMLElement | null>(null)

/** @brief Quick-access navigation items shown when search is empty. */
const quickActions: SearchItem[] = [
  { id: 'feed', label: 'Feed', icon: NewspaperIcon, path: '/app', group: 'Pages' },
  { id: 'events', label: 'Events', icon: CalendarDaysIcon, path: '/app/events', group: 'Pages' },
  { id: 'chat', label: 'Chat', icon: ChatBubbleLeftRightIcon, path: '/app/chat', group: 'Pages' },
  { id: 'members', label: 'Members', icon: UserGroupIcon, path: '/app/members', group: 'Pages' },
]

/** @brief Stub search results filtered by query. Real API integration comes later. */
const filteredResults = computed<SearchItem[]>(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return []
  return quickActions.filter(item => item.label.toLowerCase().includes(q))
})

/** @brief Group search results by their group label. */
const groupedResults = computed(() => {
  const groups: Record<string, { label: string; items: SearchItem[] }> = {}
  for (const item of filteredResults.value) {
    if (!groups[item.group]) {
      groups[item.group] = { label: item.group, items: [] }
    }
    groups[item.group].items.push(item)
  }
  return Object.values(groups)
})

/** @brief Total count of visible items for keyboard navigation. */
const totalItems = computed(() => {
  if (query.value.trim()) return filteredResults.value.length
  return quickActions.length
})

/**
 * @brief Convert a group index + item index into a flat index.
 */
function flatIndex(groupIdx: number, itemIdx: number): number {
  let count = 0
  for (let g = 0; g < groupIdx; g++) {
    count += groupedResults.value[g].items.length
  }
  return count + itemIdx
}

function navigateDown(): void {
  if (activeIndex.value < totalItems.value - 1) activeIndex.value++
}

function navigateUp(): void {
  if (activeIndex.value > 0) activeIndex.value--
}

const router = useRouter()

function selectActive(): void {
  const items = query.value.trim() ? filteredResults.value : quickActions
  const item = items[activeIndex.value]
  if (item) navigateToItem(item)
}

function navigateTo(item: SearchItem): void {
  navigateToItem(item)
}

function navigateToItem(item: SearchItem): void {
  router.push(item.path)
  close()
}

function close(): void {
  open.value = false
}

/** @brief Reset query and activeIndex when the modal opens; auto-focus input. */
watch(open, async (isOpen) => {
  if (isOpen) {
    query.value = ''
    activeIndex.value = 0
    await nextTick()
    inputRef.value?.focus()
  }
})

/** @brief Reset activeIndex when query changes. */
watch(query, () => {
  activeIndex.value = 0
})

/** @brief Cmd+K / Ctrl+K global shortcut to toggle the modal. */
const keys = useMagicKeys({
  passive: false,
  onEventFired(e) {
    if (e.key === 'k' && (e.metaKey || e.ctrlKey)) e.preventDefault()
  },
})
watch([keys['Meta_K'], keys['Ctrl_K']], ([meta, ctrl]) => {
  if (meta || ctrl) open.value = !open.value
})

/** @brief Close modal on route change. */
watch(() => router.currentRoute.value.path, () => {
  if (open.value) close()
})
</script>

<style scoped>
.search-modal-enter-active,
.search-modal-leave-active {
  transition: opacity 150ms ease, transform 150ms ease;
}

.search-modal-enter-from,
.search-modal-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
