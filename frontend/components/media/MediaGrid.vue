<!--
  @file components/media/MediaGrid.vue
  @brief Responsive thumbnail grid for post media attachments.

  Displays a grid of thumbnail images with click-to-open behaviour.
  Single items use natural aspect ratio (capped height). Multi-item
  grids use 16:9 aspect-video cells to avoid excessive vertical space.
-->

<script setup lang="ts">
/**
 * @brief MediaGrid component.
 * @param items - Array of media objects with thumbnail_url and alt_text.
 * @emits open - Emitted with the index of the clicked thumbnail.
 */
import { computed } from "vue";
import type { PostMedia } from "~/types/api";

const props = defineProps<{
  /** @brief Media items to display as thumbnails. */
  items: PostMedia[];
}>();

const emit = defineEmits<{
  (e: "open", index: number): void;
}>();

/** @brief Whether this is a multi-item grid (2+ items). */
const isMulti = computed(() => props.items.length > 1);
</script>

<template>
  <div
    v-if="items.length"
    class="grid gap-1 rounded-lg overflow-hidden max-h-[28rem]"
    :class="{
      'grid-cols-1': items.length === 1,
      'grid-cols-2': items.length === 2,
      'grid-cols-2 grid-rows-2': items.length >= 3,
    }"
  >
    <button
      v-for="(item, index) in items.slice(0, 4)"
      :key="item.id"
      class="relative overflow-hidden bg-muted focus:outline-none focus:ring-2 focus:ring-primary"
      :class="[
        isMulti ? 'aspect-video' : 'aspect-auto max-h-96',
        { 'col-span-2': items.length === 3 && index === 0 },
      ]"
      :aria-label="`View media ${index + 1}`"
      @click="emit('open', index)"
    >
      <img
        data-testid="media-thumbnail"
        :src="item.thumbnail_url || item.url"
        :alt="item.mime_type"
        class="h-full w-full object-cover"
        loading="lazy"
      >
      <span
        v-if="index === 3 && items.length > 4"
        class="absolute inset-0 flex items-center justify-center bg-black/50 text-lg font-bold text-white"
      >
        +{{ items.length - 4 }}
      </span>
    </button>
  </div>
</template>
