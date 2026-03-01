<!--
  @file components/search/SearchResults.vue
  @brief Renders tabbed search results with items or empty state.

  Receives results and activeTab as props. Each result shows title,
  snippet, type badge, and relative time. Comment results link to their
  parent post.
-->
<template>
  <div class="space-y-4">
    <ul v-if="items.length > 0" class="divide-y divide-border" role="list">
      <li v-for="item in items" :key="`${item.type}-${item.id}`" class="py-4">
        <NuxtLink
          :to="itemLink(item)"
          class="block hover:bg-accent/50 -mx-2 px-2 rounded-md transition-colors"
        >
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span
                class="rounded px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground"
              >
                {{ $t(typeToI18nKey(item.type)) }}
              </span>
              <span class="text-sm text-muted-foreground">{{
                timeAgo(item.created_at)
              }}</span>
            </div>
            <p class="font-medium text-foreground">{{ item.title }}</p>
            <p
              v-if="item.snippet"
              class="text-sm text-muted-foreground line-clamp-2"
            >
              {{ item.snippet }}
            </p>
          </div>
        </NuxtLink>
      </li>
    </ul>
    <p v-else class="py-8 text-center text-muted-foreground">
      {{ $t("search.noResults") }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief SearchResults list with type badges, links, and empty state.
 */
import type { SearchResultItem } from "~/types/api";
import { timeAgo } from "~/utils/date";

defineProps<{
  /** @brief List of search result items to render. */
  items: SearchResultItem[];
  /** @brief Active tab: all, posts, comments, users, events. */
  activeTab: string;
}>();

/**
 * @brief Map type key to i18n key for display label.
 * Returns the translation key so $t() is invoked in template context.
 */
function typeToI18nKey(type: string): string {
  const map: Record<string, string> = {
    posts: "search.posts",
    comments: "search.comments",
    users: "search.people",
    events: "search.events",
  };
  return map[type] ?? `search.${type}`;
}

/**
 * @brief Build the navigation link for a search result item.
 * Comments link to their parent post (via parent_id).
 */
function itemLink(item: SearchResultItem): string {
  if (item.type === "comments" && item.parent_id) {
    return `/app/post/${item.parent_id}`;
  }
  if (item.type === "posts") {
    return `/app/post/${item.id}`;
  }
  return "#";
}
</script>
