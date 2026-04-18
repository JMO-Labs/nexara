<!--
  @file components/admin/BrandingPreview.vue
  @brief Live preview panel showing how branding looks.
-->
<template>
  <div
    class="rounded-lg border border-border p-4"
    :style="previewStyles"
    data-testid="branding-preview"
  >
    <p
      class="mb-2 text-lg font-semibold"
      :style="{ color: branding.color_text_light || branding.color_text_dark }"
    >
      {{ branding.community_name || "Community" }}
    </p>
    <p
      class="mb-4 text-sm opacity-80"
      :style="{ color: branding.color_text_light || branding.color_text_dark }"
    >
      {{ branding.tagline || "Tagline" }}
    </p>
    <div class="flex gap-2">
      <div
        class="rounded-lg px-4 py-2 text-sm font-medium"
        :style="{
          backgroundColor: branding.color_primary,
          color: branding.color_text_light || '#ffffff',
        }"
      >
        {{ branding.landing_cta_text || "Join" }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief BrandingPreview shows a mini card with branding colors applied.
 */
import { computed } from "vue";
import type { BrandingFormData } from "~/types/api";

const props = defineProps<{
  /** @brief Current form state for preview. */
  branding: BrandingFormData;
}>();

const previewStyles = computed(() => ({
  backgroundColor: props.branding.color_surface_light || "#ffffff",
  fontFamily: props.branding.font_family || "Inter",
}));
</script>
