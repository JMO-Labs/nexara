<!--
  @file components/feed/CommentNode.vue
  @brief Recursive comment node for unlimited nesting depth.

  Renders a single comment via CommentItem, shows the inline reply form
  when this comment is being replied to, and recursively renders child
  replies with a subtle thread line for visual nesting. Reply state is
  injected from the parent CommentThread via provide/inject.
-->
<template>
  <div>
    <CommentItem
      :comment="comment"
      :highlighted="replyingToId === comment.id"
      :depth="depth"
      @reply="startReply"
    />

    <!-- Inline reply form when replying to this comment -->
    <div v-if="replyingToId === comment.id" class="mt-1 pl-9">
      <div class="mb-1 flex items-center gap-2">
        <p class="text-xs font-medium text-primary">
          {{ $t("feed.replyingTo", { username: comment.author.display_name }) }}
        </p>
        <button
          type="button"
          class="text-xs text-muted-foreground transition-colors hover:text-foreground"
          @click="cancelReply"
        >
          {{ $t("common.cancel") }}
        </button>
      </div>
      <CommentInput
        data-testid="reply-form"
        :placeholder="$t('feed.addComment')"
        :submit-label="$t('feed.submitComment')"
        @submit="handleReplySubmit"
        @react="(emoji: string) => reactToComment(comment.id, emoji)"
      />
    </div>

    <!-- Recursive child replies with thread line -->
    <div
      v-if="comment.replies?.length"
      class="relative ml-[18px] mt-1 space-y-0.5 pl-4"
    >
      <!-- Thread line connecting parent to children -->
      <div
        class="absolute bottom-2 left-0 top-0 w-px bg-border"
        aria-hidden="true"
      />
      <CommentNode
        v-for="reply in comment.replies"
        :key="reply.id"
        :comment="reply"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Recursive comment node with injected reply state.
 *
 * Injects replyingToId, replyContent, startReply, cancelReply, and
 * submitReply from the parent CommentThread to keep reply state
 * centralized regardless of nesting depth.
 */
import { inject } from "vue";
import type { Ref } from "vue";
import type { Comment } from "~/types/api";
import CommentItem from "~/components/feed/CommentItem.vue";
import CommentInput from "~/components/feed/CommentInput.vue";

const props = withDefaults(
  defineProps<{
    /** @brief The comment to display. */
    comment: Comment;
    /** @brief Nesting depth (0 = top-level). */
    depth?: number;
  }>(),
  { depth: 0 },
);

const replyingToId = inject<Ref<string | null>>("replyingToId")!;
const startReply = inject<(id: string) => void>("startReply")!;
const cancelReply = inject<() => void>("cancelReply")!;
const submitReply = inject<(parentId: string, text: string) => void>("submitReply")!;
const reactToComment = inject<(commentId: string, emoji: string) => void>("reactToComment")!;

/**
 * @brief Handle reply text submission from CommentInput.
 * @param text Trimmed reply content.
 */
function handleReplySubmit(text: string): void {
  submitReply(props.comment.id, text);
};
</script>
