<!--
  @file components/feed/CommentItem.vue
  @brief Single comment display component.

  Renders a comment with author avatar, display name, content, timestamp,
  and a Reply button. Accepts a depth prop so nested replies render with
  progressively smaller avatars for visual hierarchy.
-->
<template>
  <div
    class="group flex gap-2.5 rounded-md px-1.5 py-1 transition-colors"
    :class="{ 'bg-primary/10 ring-1 ring-primary/30': highlighted }"
  >
    <div
      class="shrink-0 rounded-full bg-muted font-bold text-muted-foreground flex items-center justify-center"
      :class="depth > 0 ? 'h-6 w-6 text-[10px]' : 'h-7 w-7 text-xs'"
    >
      {{ comment.author.display_name.charAt(0).toUpperCase() }}
    </div>
    <div class="min-w-0 flex-1">
      <p class="text-sm leading-snug">
        <span class="font-semibold text-foreground">{{
          comment.author.display_name
        }}</span>
        <span class="ml-1.5 text-muted-foreground">{{ comment.content }}</span>
      </p>
      <div class="mt-0.5 flex items-center gap-3">
        <span class="text-[11px] text-muted-foreground/60">
          {{ timeAgo(comment.created_at) }}
        </span>
        <ReactionBar
          :reactions="comment.reactions ?? []"
          target-type="comment"
          :target-id="comment.id"
          @react="onReact"
        />
        <button
          type="button"
          class="text-[11px] font-medium text-muted-foreground/60 opacity-0 transition-opacity group-hover:opacity-100 hover:text-foreground"
          @click="emit('reply', comment.id)"
        >
          {{ $t("feed.reply") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief CommentItem props and events.
 *
 * Uses inject to get reactToComment from CommentThread for reaction handling.
 */
import { inject } from "vue";
import type { Comment } from "~/types/api";
import { timeAgo } from "~/utils/date";
import ReactionBar from "~/components/feed/ReactionBar.vue";

withDefaults(
  defineProps<{
    /** @brief The comment to display. */
    comment: Comment;
    /** @brief Whether this comment is highlighted (being replied to). */
    highlighted?: boolean;
    /** @brief Nesting depth for visual scaling (0 = top-level). */
    depth?: number;
  }>(),
  { highlighted: false, depth: 0 },
);

const emit = defineEmits<{
  (e: "reply", commentId: string): void;
}>();

/** @brief Injected handler for comment reactions from CommentThread. */
const reactToComment = inject<(commentId: string, emoji: string) => void>(
  "reactToComment",
);

/**
 * @brief Handle reaction from ReactionBar and forward to parent via inject.
 * @param _targetType - Entity type (always "comment" here).
 * @param targetId - Comment ID.
 * @param emoji - Selected emoji.
 */
function onReact(
  _targetType: string,
  targetId: string,
  emoji: string,
): void {
  reactToComment?.(targetId, emoji);
}
</script>
