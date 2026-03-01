<!--
  @file components/feed/CommentThread.vue
  @brief Threaded comment display with reply state management.

  Renders a list of comments with unlimited nesting depth via the
  recursive CommentNode component. Provides reply state to all
  descendant nodes via provide/inject so only one reply form is
  open at a time. The top-level comment input lives on PostCard.
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
  (
    e: "react-comment",
    payload: { postId: string; commentId: string; emoji: string },
  ): void;
}>();

const replyingToId = ref<string | null>(null);

/** @brief Start replying to a comment by id. */
function startReply(commentId: string): void {
  replyingToId.value = commentId;
}

/** @brief Cancel the current reply. */
function cancelReply(): void {
  replyingToId.value = null;
}

/**
 * @brief Submit a reply to a specific comment.
 * @param parentId Comment ID being replied to.
 * @param text Reply text content from CommentInput.
 */
function submitReply(parentId: string, text: string): void {
  emit("add-comment", {
    postId: props.postId,
    content: text,
    parentId,
  });
  replyingToId.value = null;
}

/**
 * @brief Handle a reaction on a comment and emit to parent.
 * @param commentId - ID of the comment.
 * @param emoji - Selected emoji.
 */
function reactToComment(commentId: string, emoji: string): void {
  emit("react-comment", {
    postId: props.postId,
    commentId,
    emoji,
  });
}

provide("replyingToId", replyingToId);
provide("startReply", startReply);
provide("cancelReply", cancelReply);
provide("submitReply", submitReply);
provide("reactToComment", reactToComment);
</script>
