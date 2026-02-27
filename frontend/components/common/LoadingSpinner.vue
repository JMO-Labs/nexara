<!--
  @file components/common/LoadingSpinner.vue
  @brief Accessible loading state indicator.

  Renders an animated spinner with an accessible label.
  Respects `prefers-reduced-motion` via CSS.
-->
<template>
  <div
    class="flex items-center justify-center"
    role="status"
    :aria-label="$t('common.loading')"
  >
    <div
      :class="[
        'animate-spin rounded-full border-2 border-gray-200 dark:border-gray-600',
        'border-t-primary-600 dark:border-t-primary-400',
        sizeClasses,
      ]"
    />
    <span class="sr-only">{{ $t('common.loading') }}</span>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief LoadingSpinner component with configurable size.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** @brief Spinner size variant. */
  size?: 'sm' | 'md' | 'lg'
}>(), { size: 'md' })

const sizeClasses = computed(() => {
  const sizes = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' }
  return sizes[props.size]
})
</script>
