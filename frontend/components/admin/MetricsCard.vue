<!--
  @file components/admin/MetricsCard.vue
  @brief Admin metric display card.

  Displays a single metric with optional icon and trend indicator.
  Used in the admin dashboard grid.
-->
<template>
  <div
    class="rounded-lg border border-border bg-card p-4 shadow-sm transition-shadow hover:shadow-md"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0 flex-1">
        <p class="text-sm font-medium text-muted-foreground">
          {{ title }}
        </p>
        <p class="mt-1 truncate text-2xl font-bold text-foreground">
          {{ formattedValue }}
        </p>
        <p
          v-if="trend"
          class="mt-1 text-xs"
          :class="trendClass"
        >
          {{ trend }}
        </p>
      </div>
      <div
        v-if="icon"
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"
      >
        <span class="text-lg" aria-hidden="true">{{ icon }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief MetricsCard props and computed formatting.
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** @brief Card title (metric name). */
    title: string
    /** @brief Metric value (string or number). */
    value: string | number
    /** @brief Optional emoji or icon character. */
    icon?: string
    /** @brief Optional trend text (e.g. "+12%"). */
    trend?: string
    /** @brief Whether trend is positive (green) or negative (red). */
    trendPositive?: boolean
  }>(),
  { icon: '', trend: '', trendPositive: true },
)

/** @brief Formatted value for display. */
const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

/** @brief Tailwind class for trend text color. */
const trendClass = computed(() =>
  props.trendPositive
    ? 'text-green-600 dark:text-green-400'
    : 'text-red-600 dark:text-red-400',
)
</script>
