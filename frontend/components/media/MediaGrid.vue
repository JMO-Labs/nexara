<!--
  @file components/media/MediaGrid.vue
  @brief Responsive thumbnail grid for post media attachments.

  Displays a grid of thumbnail images with click-to-open behaviour.
  Adapts layout based on the number of items (1-4+ columns).
-->

<script setup lang="ts">
/**
 * @brief MediaGrid component.
 * @param items - Array of media objects with thumbnail_url and alt_text.
 * @emits open - Emitted with the index of the clicked thumbnail.
 */
import type { PostMedia } from "~/types/api";

defineProps<{
  /** @brief Media items to display as thumbnails. */
  items: PostMedia[];
}>();

const emit = defineEmits<{
  (e: "open", index: number): void;
}>();
</script>

<template>
  <div
    v-if="items.length"
    class="grid gap-1 rounded-lg overflow-hidden"
    :class="{
      'grid-cols-1': items.length === 1,
      'grid-cols-2': items.length === 2,
      'grid-cols-2 grid-rows-2': items.length >= 3,
    }"
  >
    <button
      v-for="(item, index) in items.slice(0, 4)"
      :key="item.id"
      class="relative aspect-square overflow-hidden bg-muted focus:outline-none focus:ring-2 focus:ring-primary"
      :class="{ 'col-span-2': items.length === 3 && index === 0 }"
      :aria-label="`View media ${index + 1}`"
      @click="emit('open', index)"
    >
      <img
        :src="item.thumbnail_url || item.url"
        :alt="item.mime_type"
        class="h-full w-full object-cover"
        loading="lazy"
      />
      <span
        v-if="index === 3 && items.length > 4"
        class="absolute inset-0 flex items-center justify-center bg-black/50 text-lg font-bold text-white"
      >
        +{{ items.length - 4 }}
      </span>
    </button>
  </div>
</template>
