<!--
  @file pages/app/subgroups/[slug].vue
  @brief Subgroup detail page with tabs (Feed, Members, Chat) and pin banner.

  Shows the subgroup header (avatar, name, privacy badge, member count),
  a policy-aware Join/Leave button, a pinned announcement banner, and
  three tabs:
  - Feed   -> scoped feed rendering (the feed store receives
              `?subgroup=<slug>`).
  - Members -> summary of roles; detail list at
              `/app/subgroups/{slug}/members`.
  - Chat   -> link out to `/app/chat/{chat_channel_id}` (chat agent owns
              that page).
-->
<template>
  <div class="space-y-6">
    <NuxtLink
      to="/app/subgroups"
      data-testid="subgroup-back"
      class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <span aria-hidden="true">&larr;</span>
      {{ $t("subgroups.backToDirectory") }}
    </NuxtLink>

    <div
      v-if="subgroupsStore.loading && !subgroupsStore.current"
      class="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground"
      data-testid="subgroup-loading"
    >
      {{ $t("common.loading") }}
    </div>

    <div
      v-else-if="!subgroupsStore.current"
      class="rounded-lg border border-dashed border-border bg-card p-8 text-center text-muted-foreground"
      data-testid="subgroup-not-found"
    >
      {{ $t("subgroups.notFound") }}
    </div>

    <template v-else-if="detail">
      <!-- Header -->
      <header
        class="flex flex-col gap-4 rounded-lg border border-border bg-card p-5 sm:flex-row sm:items-start"
        data-testid="subgroup-header"
      >
        <img
          v-if="detail.avatar_url"
          :src="detail.avatar_url"
          :alt="detail.name"
          class="h-16 w-16 flex-shrink-0 rounded-full object-cover"
        />
        <div
          v-else
          class="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground"
          aria-hidden="true"
        >
          {{ initials }}
        </div>

        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h1
              class="text-xl font-bold text-foreground"
              data-testid="subgroup-title"
            >
              {{ detail.name }}
            </h1>
            <span
              v-if="detail.is_private"
              class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
              data-testid="subgroup-private-badge"
            >
              {{ $t("subgroups.private") }}
            </span>
            <span
              class="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
              data-testid="subgroup-policy-badge"
            >
              {{ $t(`subgroups.policyShort.${detail.join_policy}`) }}
            </span>
          </div>
          <p class="text-sm text-muted-foreground">/{{ detail.slug }}</p>
          <p
            v-if="detail.description"
            class="mt-2 text-sm text-foreground"
            data-testid="subgroup-description"
          >
            {{ detail.description }}
          </p>
          <p
            class="mt-2 text-xs text-muted-foreground"
            data-testid="subgroup-member-count"
          >
            {{
              detail.member_count === 1
                ? $t("subgroups.memberCountOne")
                : $t("subgroups.memberCount", { count: detail.member_count })
            }}
          </p>
        </div>

        <div class="flex flex-shrink-0 items-start gap-2">
          <JoinButton
            :slug="detail.slug"
            :my-role="detail.my_role"
            :join-policy="detail.join_policy"
            data-testid="subgroup-join-button"
          />
        </div>
      </header>

      <!-- Pinned announcement banner -->
      <div
        v-if="detail.pinned_post_id"
        class="rounded-lg border border-primary/30 bg-primary/5 p-4"
        data-testid="subgroup-pinned-banner"
      >
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase text-primary">
              {{ $t("subgroups.pinnedPost") }}
            </p>
            <NuxtLink
              :to="`/app/post/${detail.pinned_post_id}`"
              class="text-sm font-medium text-foreground hover:underline"
              data-testid="subgroup-pinned-link"
            >
              {{ detail.pinned_post_id }}
            </NuxtLink>
          </div>
          <button
            v-if="canManage"
            type="button"
            class="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            data-testid="subgroup-unpin-button"
            @click="handleUnpin"
          >
            {{ $t("subgroups.unpinPost") }}
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <nav
        class="flex items-center gap-2 border-b border-border"
        role="tablist"
        :aria-label="$t('subgroups.title')"
      >
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :data-testid="`subgroup-tab-${tab.id}`"
          :aria-selected="activeTab === tab.id"
          :aria-controls="`subgroup-panel-${tab.id}`"
          role="tab"
          type="button"
          class="px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
          :class="
            activeTab === tab.id
              ? 'border-b-2 border-primary text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          "
          @click="activeTab = tab.id"
        >
          {{ $t(`subgroups.tabs.${tab.id}`) }}
        </button>
      </nav>

      <section
        v-if="activeTab === 'feed'"
        id="subgroup-panel-feed"
        role="tabpanel"
        data-testid="subgroup-feed-panel"
        class="rounded-lg border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
      >
        {{ $t("common.comingSoon") }}
      </section>

      <section
        v-else-if="activeTab === 'members'"
        id="subgroup-panel-members"
        role="tabpanel"
        data-testid="subgroup-members-panel"
        class="space-y-3 rounded-lg border border-border bg-card p-4"
      >
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium text-foreground">
            {{ $t("subgroups.membersTitle") }}
          </p>
          <NuxtLink
            :to="`/app/subgroups/${detail.slug}/members`"
            class="text-sm text-primary hover:underline"
            data-testid="subgroup-members-link"
          >
            {{ $t("common.next") }}
          </NuxtLink>
        </div>
      </section>

      <section
        v-else-if="activeTab === 'chat'"
        id="subgroup-panel-chat"
        role="tabpanel"
        data-testid="subgroup-chat-panel"
        class="rounded-lg border border-border bg-card p-4"
      >
        <NuxtLink
          v-if="detail.chat_channel_id"
          :to="`/app/chat/${detail.chat_channel_id}`"
          class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          data-testid="subgroup-chat-link"
        >
          {{ $t("subgroups.openChat") }}
        </NuxtLink>
        <p v-else class="text-sm text-muted-foreground">
          {{ $t("common.comingSoon") }}
        </p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Subgroup detail page with tabbed content.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useSubgroupsStore } from "~/stores/subgroups";
import { useUiStore } from "~/stores/ui";
import JoinButton from "~/components/subgroups/JoinButton.vue";

const route = useRoute();
const subgroupsStore = useSubgroupsStore();
const uiStore = useUiStore();
const { t: $t } = useI18n();

/** @brief Available tab IDs. */
type TabId = "feed" | "members" | "chat";

const tabs: Array<{ id: TabId }> = [
  { id: "feed" },
  { id: "members" },
  { id: "chat" },
];

const activeTab = ref<TabId>("feed");

/** @brief Slug taken from the dynamic route parameter. */
const slug = computed(() => String(route.params.slug ?? ""));

/** @brief Typed alias for the current subgroup from the store. */
const detail = computed(() => subgroupsStore.current);

/** @brief Initials derived from the subgroup name for the avatar fallback. */
const initials = computed(() => {
  if (!detail.value) return "?";
  const parts = detail.value.name.trim().split(/\s+/);
  const a = parts[0]?.[0] ?? "?";
  const b = parts[1]?.[0] ?? "";
  return (a + b).toUpperCase();
});

/** @brief Whether the viewer can pin/unpin or manage the subgroup. */
const canManage = computed(
  () =>
    detail.value?.my_role === "owner" || detail.value?.my_role === "moderator",
);

/** @brief Fetch the subgroup detail, showing toast on failure. */
async function loadSubgroup(): Promise<void> {
  if (!slug.value) return;
  try {
    await subgroupsStore.fetchDetail(slug.value);
  } catch (err) {
    subgroupsStore.current = null;
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  }
}

/** @brief Remove the pinned post (owner/moderator action). */
async function handleUnpin(): Promise<void> {
  if (!detail.value) return;
  try {
    await subgroupsStore.unpinPost(detail.value.slug);
    uiStore.showToast({
      type: "info",
      message: $t("subgroups.unpinned"),
    });
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  }
}

// Re-fetch when the slug changes (e.g. navigating between subgroups).
watch(slug, () => {
  loadSubgroup();
});

onMounted(loadSubgroup);
</script>
