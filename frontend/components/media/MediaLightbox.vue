<!--
  @file components/media/MediaLightbox.vue
  @brief Full-size media viewer overlay with keyboard navigation.

  Opens as a modal overlay showing the full-size image. Supports
  left/right arrow navigation and Escape to close.
-->

<script setup lang="ts">
/**
 * @brief MediaLightbox component.
 * @param items - Array of media objects.
 * @param startIndex - Index of the initially shown item.
 * @emits close - Emitted when the lightbox should be closed.
 */
import { ref, computed, onMounted, onUnmounted } from "vue";
import type { PostMedia } from "~/types/api";

const props = defineProps<{
  /** @brief Media items available for viewing. */
  items: PostMedia[];
  /** @brief Index of the item to show first. */
  startIndex: number;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const currentIndex = ref(props.startIndex);

/** @brief Currently displayed media item. */
const current = computed(() => props.items[currentIndex.value]);

/** @brief Navigate to the previous item. */
function prev(): void {
  if (currentIndex.value > 0) currentIndex.value--;
}

/** @brief Navigate to the next item. */
function next(): void {
  if (currentIndex.value < props.items.length - 1) currentIndex.value++;
}

/** @brief Handle keyboard events for navigation and close. */
function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Escape") emit("close");
  if (e.key === "ArrowLeft") prev();
  if (e.key === "ArrowRight") next();
}

onMounted(() => document.addEventListener("keydown", onKeydown));
onUnmounted(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      role="dialog"
      aria-modal="true"
      :aria-label="`Media ${currentIndex + 1} of ${items.length}`"
      @click.self="emit('close')"
    >
      <!-- Close button -->
      <button
        class="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        :aria-label="$t('common.close')"
        @click="emit('close')"
      >
        &times;
      </button>

      <!-- Previous -->
      <button
        v-if="currentIndex > 0"
        class="absolute left-4 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
        :aria-label="$t('common.previous')"
        @click="prev"
      >
        &larr;
      </button>

      <!-- Image -->
      <img
        v-if="current"
        :src="current.url"
        :alt="current.mime_type"
        class="max-h-[90vh] max-w-[90vw] object-contain"
      >

      <!-- Next -->
      <button
        v-if="currentIndex < items.length - 1"
        class="absolute right-4 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
        :aria-label="$t('common.next')"
        @click="next"
      >
        &rarr;
      </button>

      <!-- Counter -->
      <span class="absolute bottom-4 text-sm text-white/70">
        {{ currentIndex + 1 }} / {{ items.length }}
      </span>
    </div>
  </Teleport>
</template>
