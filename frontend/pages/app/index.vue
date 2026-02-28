<!--
  @file pages/app/index.vue
  @brief Activity feed page — the main page after login.

  Displays the post composer and an infinite-scroll feed of posts.
  New posts arrive in real-time via SSE feed_update events. The layout
  handles the 3-column grid; this page only provides feed content.
-->
<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-bold text-foreground">
      {{ $t("feed.title") }}
    </h1>

    <!-- Post composer -->
    <PostComposer />

    <!-- Loading state -->
    <LoadingSpinner
      v-if="feedStore.loading && feedStore.posts.length === 0"
      size="lg"
    />

    <!-- Feed with entry animation for SSE live posts -->
    <TransitionGroup name="feed-post" tag="div" class="space-y-4">
      <PostCard
        v-for="post in feedStore.posts"
        :key="post.id"
        :post="post"
        @react="handleReaction"
      />
    </TransitionGroup>

    <!-- Load more / end of feed -->
    <div class="py-4 text-center">
      <button
        v-if="feedStore.hasMore && !feedStore.loading"
        class="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        @click="feedStore.fetchPosts()"
      >
        {{ $t("feed.loadMore") }}
      </button>
      <LoadingSpinner v-else-if="feedStore.loading" />
      <p
        v-else-if="!feedStore.hasMore && feedStore.posts.length > 0"
        class="text-sm text-muted-foreground"
      >
        {{ $t("feed.noMorePosts") }}
      </p>
      <p
        v-else-if="!feedStore.loading && feedStore.posts.length === 0"
        class="text-sm text-muted-foreground"
      >
        {{ $t("feed.emptyFeed") }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Feed page setup with store integration.
 *
 * SSE real-time updates are handled at the layout level (default.vue).
 */
import { onMounted } from "vue";
import { useFeedStore } from "~/stores/feed";
import PostComposer from "~/components/feed/PostComposer.vue";
import PostCard from "~/components/feed/PostCard.vue";
import LoadingSpinner from "~/components/common/LoadingSpinner.vue";

const feedStore = useFeedStore();

function handleReaction(postId: string, emoji: string): void {
  feedStore.addReaction(postId, emoji);
}

onMounted(async () => {
  await feedStore.fetchPosts();
});
</script>

<style scoped>
.feed-post-enter-active {
  transition: all 0.3s ease-out;
}

.feed-post-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}

.feed-post-move {
  transition: transform 0.3s ease;
}
</style>
