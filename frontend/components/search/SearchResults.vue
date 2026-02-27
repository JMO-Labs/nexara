<!--
  @file components/search/SearchResults.vue
  @brief Renders tabbed search results with items or empty state.

  Receives results and activeTab as props. Each result shows title,
  snippet, type badge, and relative time.
-->
<template>
  <div class="space-y-4">
    <ul
      v-if="items.length > 0"
      class="divide-y divide-border"
      role="list"
    >
      <li
        v-for="item in items"
        :key="`${item.type}-${item.id}`"
        class="py-4"
      >
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <span
              class="rounded px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground"
            >
              {{ typeLabel(item.type) }}
            </span>
            <span class="text-sm text-muted-foreground">{{ timeAgo(item.created_at) }}</span>
          </div>
          <p class="font-medium text-foreground">{{ item.title }}</p>
          <p v-if="item.snippet" class="text-sm text-muted-foreground line-clamp-2">
            {{ item.snippet }}
          </p>
        </div>
      </li>
    </ul>
    <p
      v-else
      class="py-8 text-center text-muted-foreground"
    >
      {{ $t('search.noResults') }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief SearchResults list with type badges and empty state.
 */
import type { SearchResultItem } from '~/types/api'
import { timeAgo } from '~/utils/date'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  /** @brief List of search result items to render. */
  items: SearchResultItem[]
  /** @brief Active tab: all, posts, users, events. */
  activeTab: string
}>()

const { t: $t } = useI18n()

/**
 * @brief Map type key to display label.
 */
function typeLabel(type: string): string {
  const map: Record<string, string> = {
    posts: $t('search.posts'),
    users: $t('search.people'),
    events: $t('search.events'),
  }
  return map[type] ?? type
}
</script>
