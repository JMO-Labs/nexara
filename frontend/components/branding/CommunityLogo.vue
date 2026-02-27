<!--
  @file components/branding/CommunityLogo.vue
  @brief Displays the community logo (dark/light variant) or text fallback.

  Switches between light and dark logo URLs based on the current dark mode
  state. Falls back to the community name as text when no logo is uploaded.
-->

<script setup lang="ts">
/**
 * @brief CommunityLogo component.
 * @param size - Logo size in pixels (default 40).
 */
import { computed } from 'vue'
import { useBranding } from '~/composables/useBranding'
import { useDarkMode } from '~/composables/useDarkMode'

const props = withDefaults(defineProps<{
  /** @brief Logo dimension in pixels. */
  size?: number
}>(), { size: 40 })

const { branding } = useBranding()
const { isDark } = useDarkMode()

/** @brief Resolved logo URL based on dark mode state. */
const logoUrl = computed(() => {
  if (isDark.value && branding.value.logo_dark_url) {
    return branding.value.logo_dark_url
  }
  return branding.value.logo_light_url
})

/** @brief Whether to show the text fallback. */
const showText = computed(() => !logoUrl.value)
</script>

<template>
  <img
    v-if="!showText"
    :src="logoUrl!"
    :alt="branding.community_name"
    :width="props.size"
    :height="props.size"
    class="object-contain"
  />
  <span
    v-else
    class="font-bold text-lg truncate"
    :aria-label="branding.community_name"
  >
    {{ branding.community_name }}
  </span>
</template>
