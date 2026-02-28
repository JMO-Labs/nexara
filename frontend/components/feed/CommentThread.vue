<!--
  @file components/feed/CommentThread.vue
  @brief Threaded comment display and reply input.

  Renders a list of comments with unlimited nesting depth via the
  recursive CommentNode component. Provides reply state to all
  descendant nodes via provide/inject so only one reply form is
  open at a time. Includes a new comment form at the bottom.
-->
<template>
  <div class="space-y-1">
    <!-- Load older comments button -->
    <button
      v-if="showLoadMore"
      class="flex w-full items-center justify-center gap-1.5 rounded-md py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      @click="emit('load-more')"
    >
      <ArrowPathIcon class="h-3.5 w-3.5" />
      {{ $t("feed.loadOlderComments") }}
    </button>

    <!-- Comment tree -->
    <CommentNode
      v-for="comment in comments"
      :key="comment.id"
      :comment="comment"
      :depth="0"
    />

    <!-- New comment form -->
    <form
      data-testid="comment-form"
      class="mt-2 flex gap-2"
      @submit.prevent="handleSubmit"
    >
      <input
        v-model="newComment"
        data-testid="comment-input"
        type="text"
        :placeholder="$t('feed.addComment')"
        :aria-label="$t('feed.addComment')"
        class="flex-1 rounded-md border border-input bg-muted px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
      >
      <button
        type="submit"
        :disabled="!newComment.trim()"
        class="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      >
        {{ $t("feed.submitComment") }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief CommentThread — owns reply state and provides it to CommentNode tree.
 */
import { ref, provide } from "vue";
import { ArrowPathIcon } from "@heroicons/vue/24/outline";
import type { Comment } from "~/types/api";
import CommentNode from "~/components/feed/CommentNode.vue";

const props = defineProps<{
  /** @brief List of top-level comments with nested replies. */
  comments: Comment[];
  /** @brief ID of the parent post. */
  postId: string;
  /** @brief Whether more older comments can be loaded. */
  showLoadMore?: boolean;
}>();

const emit = defineEmits<{
  (
    e: "add-comment",
    payload: { postId: string; content: string; parentId: string | null },
  ): void;
  (e: "load-more"): void;
}>();

const newComment = ref("");
const replyingToId = ref<string | null>(null);
const replyContent = ref("");

/** @brief Start replying to a comment by id. */
function startReply(commentId: string): void {
  replyingToId.value = commentId;
  replyContent.value = "";
}

/** @brief Cancel the current reply. */
function cancelReply(): void {
  replyingToId.value = null;
  replyContent.value = "";
}

/** @brief Submit a reply to a specific comment. */
function submitReply(parentId: string): void {
  if (!replyContent.value.trim()) return;
  emit("add-comment", {
    postId: props.postId,
    content: replyContent.value,
    parentId,
  });
  replyContent.value = "";
  replyingToId.value = null;
}

function handleSubmit(): void {
  if (!newComment.value.trim()) return;
  emit("add-comment", {
    postId: props.postId,
    content: newComment.value,
    parentId: null,
  });
  newComment.value = "";
}

provide("replyingToId", replyingToId);
provide("replyContent", replyContent);
provide("startReply", startReply);
provide("cancelReply", cancelReply);
provide("submitReply", submitReply);
</script>
