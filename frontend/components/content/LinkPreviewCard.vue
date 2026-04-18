<!--
  @file components/content/LinkPreviewCard.vue
  @brief Renders an OG link preview card with image, title, description, site name.

  Clickable card that opens URL in new tab.
  Fallback when no image. Clean, modern design.
-->
<template>
  <a
    :href="preview.url"
    target="_blank"
    rel="noopener noreferrer"
    class="flex overflow-hidden rounded-lg border border-border bg-card transition-colors hover:bg-card/80"
    data-testid="link-preview-card"
  >
    <div
      class="flex flex-1 flex-col sm:flex-row"
      :class="preview.image_url ? 'sm:flex-row' : ''"
    >
      <!-- Image (left on desktop, top on mobile) -->
      <div
        v-if="preview.image_url"
        class="h-32 shrink-0 sm:h-auto sm:w-48"
      >
        <img
          :src="preview.image_url"
          :alt="preview.title ?? ''"
          class="h-full w-full object-cover"
        >
      </div>
      <div
        v-else
        class="flex h-24 shrink-0 items-center justify-center bg-muted sm:w-32"
      >
        <span class="text-4xl text-muted-foreground">🔗</span>
      </div>

      <!-- Content -->
      <div class="flex flex-1 flex-col justify-center p-4">
        <h3
          v-if="preview.title"
          class="font-semibold text-foreground line-clamp-2"
        >
          {{ preview.title }}
        </h3>
        <p
          v-if="preview.description"
          class="mt-1 line-clamp-2 text-sm text-muted-foreground"
        >
          {{ preview.description }}
        </p>
        <p
          v-if="preview.site_name"
          class="mt-2 text-xs text-muted-foreground"
        >
          {{ preview.site_name }}
        </p>
      </div>
    </div>
  </a>
</template>

<script setup lang="ts">
/**
 * @brief LinkPreviewCard — displays OG link preview metadata.
 */
import type { LinkPreview } from "~/types/api";

defineProps<{
  /** @brief Link preview metadata. */
  preview: LinkPreview;
}>();
</script>
