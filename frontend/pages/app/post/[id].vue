<!--
  @file pages/app/post/[id].vue
  @brief Single post detail page with full comment thread.

  Displays a single post with its complete comment thread and
  allows adding new comments and reactions.
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
 * @brief Post detail page with comments loading.
 */
import { ref, computed, onMounted } from "vue";
import { useApi } from "~/composables/useApi";
import PostCard from "~/components/feed/PostCard.vue";
import CommentThread from "~/components/feed/CommentThread.vue";
import LoadingSpinner from "~/components/common/LoadingSpinner.vue";
import type { Post, Comment } from "~/types/api";
import { buildCommentTree } from "~/utils/comments";

/** @brief Paginated response shape for the comments endpoint. */
interface PaginatedComments {
  items: Comment[];
  cursor: string | null;
  has_more: boolean;
}

const props = defineProps<{ id: string }>();

const api = useApi();
const post = ref<Post | null>(null);
const flatComments = ref<Comment[]>([]);
const commentCursor = ref<string | null>(null);
const hasMore = ref(false);
const loading = ref(true);
const error = ref("");

/** @brief Flat comments nested into a tree for threaded display. */
const comments = computed<Comment[]>(() => buildCommentTree(flatComments.value));

/** @brief Resolved route ID for the post. */
function resolveRouteId(): string {
  return (
    props.id ||
    (typeof window !== "undefined"
      ? window.location.pathname.split("/").pop() ?? ""
      : "")
  );
}

function handleReaction(_postId: string, emoji: string): void {
  if (!post.value) return;
  const existing = post.value.reactions.find((r) => r.emoji === emoji);
  if (existing) {
    existing.reacted_by_me = !existing.reacted_by_me;
    existing.count += existing.reacted_by_me ? 1 : -1;
  } else {
    post.value.reactions.push({ emoji, count: 1, reacted_by_me: true });
  }
}

async function handleAddComment(payload: {
  postId: string;
  content: string;
  parentId: string | null;
}): Promise<void> {
  try {
    const newComment = await api.post<Comment>(
      `/posts/${payload.postId}/comments`,
      {
        content: payload.content,
        parent_id: payload.parentId,
      },
    );
    flatComments.value.unshift(newComment);
    if (post.value) post.value.comment_count++;
  } catch {
    /* Toast handled by global error handler */
  }
}

/** @brief Fetch next page of comments and append. */
async function loadMore(): Promise<void> {
  const routeId = resolveRouteId();
  const params = new URLSearchParams();
  if (commentCursor.value) params.set("cursor", commentCursor.value);
  try {
    const data = await api.get<PaginatedComments>(
      `/posts/${routeId}/comments?${params}`,
    );
    flatComments.value.push(...data.items);
    commentCursor.value = data.cursor;
    hasMore.value = data.has_more;
  } catch {
    /* Toast handled by global error handler */
  }
}

onMounted(async () => {
  try {
    const routeId = resolveRouteId();
    post.value = await api.get<Post>(`/posts/${routeId}`);
    const data = await api.get<PaginatedComments>(
      `/posts/${routeId}/comments`,
    );
    flatComments.value = data.items;
    commentCursor.value = data.cursor;
    hasMore.value = data.has_more;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load post";
  } finally {
    loading.value = false;
  }
});
</script>
