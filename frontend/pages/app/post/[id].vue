<!--
  @file pages/app/post/[id].vue
  @brief Single post detail page with full comment thread.

  Displays a single post with its complete comment thread and
  allows adding new comments and reactions.  State is backed by
  the feed store so SSE real-time updates are reflected immediately.
-->
<template>
  <div class="space-y-4">
    <NuxtLink to="/app" class="text-sm text-primary hover:underline">
      &larr; {{ $t("feed.title") }}
    </NuxtLink>

    <LoadingSpinner v-if="loading" size="lg" />

    <template v-if="post">
      <PostCard :post="post" @react="handleReaction" />

      <div class="rounded-lg border border-border bg-card p-4">
        <h2 class="mb-4 text-lg font-semibold text-card-foreground">
          {{ $t("feed.comments") }} ({{ post.comment_count }})
        </h2>
        <div class="max-h-[32rem] overflow-y-auto">
          <CommentThread
            :comments="comments"
            :post-id="post.id"
            :show-load-more="hasMore"
            @add-comment="handleAddComment"
            @load-more="loadMore"
            @react-comment="handleReactComment"
          />
        </div>
      </div>
    </template>

    <div
      v-if="error"
      class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive"
      role="alert"
    >
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Post detail page wired to the feed store for SSE reactivity.
 *
 * Fetches the post and comments into the shared feed store on mount
 * so that real-time SSE events (comments, reactions) update this page.
 */
import { ref, computed, onMounted } from "vue";
import { useApi } from "~/composables/useApi";
import { useFeedStore } from "~/stores/feed";
import { useUiStore } from "~/stores/ui";
import PostCard from "~/components/feed/PostCard.vue";
import CommentThread from "~/components/feed/CommentThread.vue";
import LoadingSpinner from "~/components/common/LoadingSpinner.vue";
import type { Post, Comment } from "~/types/api";
import { buildCommentTree } from "~/utils/comments";

const props = defineProps<{ id: string }>();

const api = useApi();
const feedStore = useFeedStore();
const uiStore = useUiStore();

const loading = ref(true);
const error = ref("");

/** @brief Resolved route ID for the post. */
function resolveRouteId(): string {
  return (
    props.id ||
    (typeof window !== "undefined"
      ? window.location.pathname.split("/").pop() ?? ""
      : "")
  );
}

/** @brief Post from the shared feed store (SSE-reactive). */
const post = computed<Post | null>(
  () => feedStore.posts.find((p) => p.id === resolveRouteId()) ?? null,
);

/** @brief Paginated comment entry from the feed store. */
const commentEntry = computed(() => feedStore.commentsByPost[resolveRouteId()]);

/** @brief Flat comments nested into a tree for threaded display. */
const comments = computed<Comment[]>(() =>
  buildCommentTree(commentEntry.value?.items ?? []),
);

/** @brief Whether more comment pages can be fetched from the server. */
const hasMore = computed(() => commentEntry.value?.hasMore ?? false);

/** @brief Show an error toast from a caught exception. */
function toastError(err: unknown, fallback: string): void {
  uiStore.showToast({
    type: "error",
    message: err instanceof Error ? err.message : fallback,
  });
}

async function handleReaction(_postId: string, emoji: string): Promise<void> {
  try {
    await feedStore.addReaction(resolveRouteId(), emoji);
  } catch (err) {
    toastError(err, "Failed to react");
  }
}

async function handleReactComment(payload: {
  postId: string;
  commentId: string;
  emoji: string;
}): Promise<void> {
  try {
    await feedStore.addCommentReaction(
      payload.postId,
      payload.commentId,
      payload.emoji,
    );
  } catch (err) {
    toastError(err, "Failed to add reaction");
  }
}

async function handleAddComment(payload: {
  postId: string;
  content: string;
  parentId: string | null;
}): Promise<void> {
  try {
    await feedStore.addComment(
      payload.postId,
      payload.content,
      payload.parentId,
    );
  } catch (err) {
    toastError(err, "Failed to add comment");
  }
}

/** @brief Fetch next page of comments via the feed store. */
async function loadMore(): Promise<void> {
  try {
    await feedStore.fetchComments(resolveRouteId());
  } catch (err) {
    toastError(err, "Failed to load comments");
  }
}

onMounted(async () => {
  try {
    const id = resolveRouteId();
    const postData = await api.get<Post>(`/posts/${id}`);
    feedStore.upsertPost(postData);
    await feedStore.fetchComments(id, true);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load post";
  } finally {
    loading.value = false;
  }
});
</script>
