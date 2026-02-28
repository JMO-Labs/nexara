<!--
  @file components/feed/PostComposer.vue
  @brief New post creation form with Markdown input and media attachment.

  Provides a textarea for composing Markdown content and a submit button.
  Emits a `submit` event with the content and attached media IDs.
-->
<template>
  <form
    class="rounded-lg border border-border bg-card p-4 shadow-sm"
    @submit.prevent="handleSubmit"
  >
    <textarea
      v-model="content"
      :placeholder="$t('feed.createPost')"
      :aria-label="$t('feed.createPost')"
      class="w-full resize-none rounded-md border-0 bg-muted p-3 text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
      rows="3"
    />
    <div class="mt-2 flex items-center justify-between">
      <button
        type="button"
        class="text-sm text-muted-foreground transition-colors hover:text-foreground"
        :aria-label="$t('feed.attachMedia')"
      >
        {{ $t("feed.attachMedia") }}
      </button>
      <button
        type="submit"
        :disabled="!content.trim()"
        class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      >
        {{ $t("feed.submit") }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief PostComposer component state and event handling.
 */
import { ref } from "vue";

const content = ref("");

const emit = defineEmits<{
  /** @brief Emitted with content and media IDs when the form is submitted. */
  (e: "submit", payload: { content: string; mediaIds: string[] }): void;
}>();

/** @brief Submit the post and clear the form. */
function handleSubmit(): void {
  if (!content.value.trim()) return;
  emit("submit", { content: content.value, mediaIds: [] });
  content.value = "";
}
</script>
