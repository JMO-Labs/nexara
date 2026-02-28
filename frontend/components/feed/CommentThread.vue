<!--
  @file components/feed/CommentThread.vue
  @brief Threaded comment display and reply input.

  Renders a list of comments with nested replies. Provides an input
  form at the bottom for adding new top-level comments.
-->
<template>
  <div class="space-y-3">
    <!-- Comment list -->
    <div v-for="comment in comments" :key="comment.id" class="space-y-2">
      <CommentItem :comment="comment" />
      <!-- Nested replies -->
      <div
        v-if="comment.replies?.length"
        class="ml-8 space-y-2 border-l-2 border-border pl-4"
      >
        <CommentItem
          v-for="reply in comment.replies"
          :key="reply.id"
          :comment="reply"
        />
      </div>
    </div>

    <!-- New comment form -->
    <form
      data-testid="comment-form"
      class="flex gap-2"
      @submit.prevent="handleSubmit"
    >
      <input
        v-model="newComment"
        data-testid="comment-input"
        type="text"
        :placeholder="$t('feed.addComment')"
        :aria-label="$t('feed.addComment')"
        class="flex-1 rounded-md border border-input bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
      />
      <button
        type="submit"
        :disabled="!newComment.trim()"
        class="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      >
        {{ $t("feed.submitComment") }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief CommentThread component props and event handling.
 */
import { ref } from "vue";
import type { Comment } from "~/types/api";
import CommentItem from "~/components/feed/CommentItem.vue";

const props = defineProps<{
  /** @brief List of top-level comments with nested replies. */
  comments: Comment[];
  /** @brief ID of the parent post. */
  postId: string;
}>();

const emit = defineEmits<{
  (
    e: "add-comment",
    payload: { postId: string; content: string; parentId: string | null },
  ): void;
}>();

const newComment = ref("");

function handleSubmit(): void {
  if (!newComment.value.trim()) return;
  emit("add-comment", {
    postId: props.postId,
    content: newComment.value,
    parentId: null,
  });
  newComment.value = "";
}
</script>
