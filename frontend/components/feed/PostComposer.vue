<!--
  @file components/feed/PostComposer.vue
  @brief New post creation form with Markdown input and media attachment.

  Provides a textarea for composing Markdown content and a submit button.
  Emits a `submit` event with the content and attached media IDs.
-->
<template>
  <form
    class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
    @submit.prevent="handleSubmit"
  >
    <textarea
      v-model="content"
      :placeholder="$t('feed.createPost')"
      :aria-label="$t('feed.createPost')"
      class="w-full resize-none rounded-lg border-0 bg-gray-50 p-3 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
      rows="3"
    />
    <div class="mt-2 flex items-center justify-between">
      <button
        type="button"
        class="text-sm text-gray-500 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400"
        :aria-label="$t('feed.attachMedia')"
      >
        {{ $t('feed.attachMedia') }}
      </button>
      <button
        type="submit"
        :disabled="!content.trim()"
        class="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {{ $t('feed.submit') }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief PostComposer component state and event handling.
 */
import { ref } from 'vue'

const content = ref('')

const emit = defineEmits<{
  /** @brief Emitted with content and media IDs when the form is submitted. */
  (e: 'submit', payload: { content: string; mediaIds: string[] }): void
}>()

/** @brief Submit the post and clear the form. */
function handleSubmit(): void {
  if (!content.value.trim()) return
  emit('submit', { content: content.value, mediaIds: [] })
  content.value = ''
}
</script>
