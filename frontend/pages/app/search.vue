<!--
  @file pages/app/search.vue
  @brief Search results page with tabs and load more.

  Gets q from route query. Tabs: All, Posts, People, Events.
  Each tab shows results for that type. Load more with cursor pagination.
-->
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-foreground">
      {{ $t("common.search") }}
    </h1>

    <SearchBar v-model="queryInput" />

    <template v-if="queryFromRoute.length >= 2">
      <!-- Tabs -->
      <ul
        class="flex flex-wrap gap-1 border-b border-border text-sm font-medium text-muted-foreground"
        role="tablist"
      >
        <li v-for="tab in tabs" :key="tab.id">
          <button
            type="button"
            class="inline-block rounded-t-lg border-b-2 px-4 py-3 transition-colors hover:border-muted-foreground hover:text-foreground"
            :class="{
              'border-primary text-foreground': activeTab === tab.id,
              'border-transparent': activeTab !== tab.id,
            }"
            role="tab"
            @click="activeTab = tab.id"
          >
            {{ $t(tab.label) }}
          </button>
        </li>
      </ul>

      <!-- Results -->
      <SearchResults :items="displayItems" :active-tab="activeTab" />

      <!-- Load more -->
      <div v-if="hasMore && displayItems.length > 0" class="text-center">
        <button
          class="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          :disabled="loading"
          @click="loadMore"
        >
          {{ loading ? $t("common.loading") : $t("search.loadMore") }}
        </button>
      </div>
    </template>

    <p
      v-else-if="queryFromRoute && queryFromRoute.length < 2"
      class="text-muted-foreground"
    >
      {{ $t("search.noResults") }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Search page with tabs and cursor pagination.
 */
import { ref, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { useApi } from "~/composables/useApi";
import SearchBar from "~/components/search/SearchBar.vue";
import SearchResults from "~/components/search/SearchResults.vue";
import type { SearchResponse, SearchResultItem } from "~/types/api";

const route = useRoute();
const api = useApi();

const queryInput = ref("");
const activeTab = ref("all");
const loading = ref(false);
const searchData = ref<SearchResponse | null>(null);
const cursors = ref<Record<string, string | null>>({});

const tabs = [
  { id: "all", label: "search.all" },
  { id: "posts", label: "search.posts" },
  { id: "comments", label: "search.comments" },
  { id: "people", label: "search.people" },
  { id: "events", label: "search.events" },
];

const queryFromRoute = computed(() => (route.query.q as string) || "");

const displayItems = computed((): SearchResultItem[] => {
  if (!searchData.value) return [];
  if (activeTab.value === "all") {
    const items: SearchResultItem[] = [];
    const order = ["posts", "comments", "users", "events"];
    for (const t of order) {
      const r = searchData.value.results[t];
      if (r) items.push(...r.items);
    }
    return items;
  }
  const key = activeTab.value === "people" ? "users" : activeTab.value;
  return searchData.value.results[key]?.items ?? [];
});

const hasMore = computed(() => {
  if (!searchData.value) return false;
  if (activeTab.value === "all") {
    return Object.values(searchData.value.results).some(
      (r) => r.next_cursor != null,
    );
  }
  const key = activeTab.value === "people" ? "users" : activeTab.value;
  return (searchData.value.results[key]?.next_cursor ?? null) != null;
});

async function fetchSearch(cursor: string | null = null): Promise<void> {
  const q = queryFromRoute.value;
  if (!q || q.length < 2) return;

  loading.value = true;
  try {
    const types = "posts,users,events,comments";
    const params = new URLSearchParams({ q, types, limit: "20" });
    if (cursor) params.set("cursor", cursor);
    const data = await api.get<SearchResponse>(`/search?${params}`);
    if (cursor) {
      if (!searchData.value) searchData.value = data;
      else {
        for (const [k, v] of Object.entries(data.results)) {
          const existing = searchData.value.results[k];
          if (existing) {
            existing.items.push(...v.items);
            existing.total = v.total;
            existing.next_cursor = v.next_cursor;
          } else {
            searchData.value.results[k] = v;
          }
        }
      }
    } else {
      searchData.value = data;
    }
  } finally {
    loading.value = false;
  }
}

function loadMore(): void {
  const key = activeTab.value === "people" ? "users" : activeTab.value;
  let next: string | null = null;
  if (activeTab.value === "all") {
    next =
      Object.values(searchData.value?.results ?? {}).find((r) => r.next_cursor)
        ?.next_cursor ?? null;
  } else {
    next = searchData.value?.results[key]?.next_cursor ?? null;
  }
  if (next) fetchSearch(next);
}

watch(
  () => route.query.q,
  (q) => {
    queryInput.value = (typeof q === "string" ? q : "") || "";
    if (q && q.length >= 2) {
      searchData.value = null;
      cursors.value = {};
      fetchSearch();
    }
  },
  { immediate: true },
);
</script>
