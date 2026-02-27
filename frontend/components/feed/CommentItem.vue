<!--
  @file components/feed/CommentItem.vue
  @brief Single comment display component.

  Renders a comment with author info, content, and timestamp.
  Extracted as a subcomponent of CommentThread for reuse in
  both top-level and nested reply rendering.
-->
<template>
  <div class="flex gap-2">
    <div
      class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground"
    >
      {{ comment.author.display_name.charAt(0).toUpperCase() }}
    </div>
    <div class="flex-1">
      <p class="text-sm">
        <span class="font-semibold text-foreground">{{
          comment.author.display_name
        }}</span>
        <span class="ml-1 text-muted-foreground">{{ comment.content }}</span>
      </p>
      <p class="text-xs text-muted-foreground/70">
        {{ timeAgo(comment.created_at) }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief CommentItem props.
 */
import type { Comment } from "~/types/api";
import { timeAgo } from "~/utils/date";

defineProps<{
  /** @brief The comment to display. */
  comment: Comment;
}>();
</script>
