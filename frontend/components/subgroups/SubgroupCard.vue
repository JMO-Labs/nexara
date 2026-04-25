<!--
  @file components/subgroups/SubgroupCard.vue
  @brief Compact summary card for a single subgroup in the directory.

  Shows avatar, name, description, privacy badge, join policy, and
  a "View" link to the subgroup detail page. Clicking anywhere on the
  card (except inner links) navigates to the detail route for improved UX.
-->
<template>
  <NuxtLink
    :to="`/app/subgroups/${subgroup.slug}`"
    :data-testid="`subgroup-card-${subgroup.slug}`"
    class="group flex flex-col gap-3 rounded-lg border border-border bg-card p-4 shadow-sm transition-colors hover:bg-card/80 focus:outline-none focus:ring-2 focus:ring-ring"
    :aria-label="subgroup.name"
  >
    <div class="flex items-start gap-3">
      <img
        v-if="subgroup.avatar_url"
        :src="subgroup.avatar_url"
        :alt="subgroup.name"
        class="h-12 w-12 flex-shrink-0 rounded-full object-cover"
      />
      <div
        v-else
        class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-primary text-base font-semibold text-primary-foreground"
        aria-hidden="true"
      >
        {{ initials }}
      </div>
      <div class="min-w-0 flex-1">
        <p
          class="truncate font-semibold text-card-foreground"
          data-testid="subgroup-card-name"
        >
          {{ subgroup.name }}
        </p>
        <p class="truncate text-xs text-muted-foreground">
          /{{ subgroup.slug }}
        </p>
      </div>
      <span
        v-if="subgroup.is_private"
        data-testid="subgroup-card-private"
        class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
      >
        {{ $t("subgroups.private") }}
      </span>
    </div>

    <p
      v-if="subgroup.description"
      class="line-clamp-2 text-sm text-muted-foreground"
      data-testid="subgroup-card-description"
    >
      {{ subgroup.description }}
    </p>

    <div
      class="mt-auto flex items-center justify-between gap-2 text-xs text-muted-foreground"
    >
      <span
        class="inline-flex items-center rounded-full bg-muted px-2 py-0.5"
        data-testid="subgroup-card-policy"
      >
        {{ $t(`subgroups.policyShort.${subgroup.join_policy}`) }}
      </span>
      <span class="font-medium text-foreground">
        {{ $t("subgroups.title") }}
        <span aria-hidden="true" class="text-muted-foreground">&rarr;</span>
      </span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
/**
 * @brief Subgroup summary card used in the directory grid.
 */
import { computed } from "vue";
import type { Subgroup } from "~/types/api";

const props = defineProps<{
  /** @brief The subgroup to summarize. */
  subgroup: Subgroup;
}>();

/** @brief Two-letter fallback initials derived from the subgroup name. */
const initials = computed(() => {
  const parts = props.subgroup.name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "?";
  const second = parts[1]?.[0] ?? "";
  return (first + second).toUpperCase();
});
</script>
