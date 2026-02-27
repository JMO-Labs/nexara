<!--
  @file pages/app/index.vue
  @brief Activity feed page — the main page after login.

  Displays the post composer and an infinite-scroll feed of posts.
  New posts arrive in real-time via SSE feed_update events.
-->
<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
      {{ $t('feed.title') }}
    </h1>

    <!-- Post composer -->
    <PostComposer @submit="handleCreatePost" />

    <!-- Loading state -->
    <LoadingSpinner v-if="feedStore.loading && feedStore.posts.length === 0" size="lg" />

    <!-- Feed -->
    <PostCard
      v-for="post in feedStore.posts"
      :key="post.id"
      :post="post"
      @react="handleReaction"
    />

    <!-- Load more / end of feed -->
    <div class="py-4 text-center">
      <button
        v-if="feedStore.hasMore && !feedStore.loading"
        class="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        @click="feedStore.fetchPosts()"
      >
        {{ $t('feed.loadMore') }}
      </button>
      <LoadingSpinner v-else-if="feedStore.loading" />
      <p v-else-if="!feedStore.hasMore && feedStore.posts.length > 0" class="text-sm text-gray-500">
        {{ $t('feed.noMorePosts') }}
      </p>
      <p v-else-if="!feedStore.loading && feedStore.posts.length === 0" class="text-sm text-gray-500">
        {{ $t('feed.emptyFeed') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Feed page setup with store integration and SSE real-time updates.
 */
import { onMounted, onUnmounted } from 'vue'
import { useFeedStore } from '~/stores/feed'
import { useAuthStore } from '~/stores/auth'
import { useSSE } from '~/composables/useSSE'
import PostComposer from '~/components/feed/PostComposer.vue'
import PostCard from '~/components/feed/PostCard.vue'
import LoadingSpinner from '~/components/common/LoadingSpinner.vue'
import type { Post } from '~/types/api'

const feedStore = useFeedStore()
const authStore = useAuthStore()

const { connect, disconnect } = useSSE((type, data) => {
  if (type === 'feed_update' && data) {
    feedStore.prependPost(data as Post)
  }
})

async function handleCreatePost(payload: { content: string; mediaIds: string[] }): Promise<void> {
  await feedStore.createPost(payload.content, payload.mediaIds)
}

function handleReaction(postId: string, emoji: string): void {
  feedStore.addReaction(postId, emoji)
}

onMounted(async () => {
  await feedStore.fetchPosts()
  if (authStore.isAuthenticated) {
    connect()
  }
})

onUnmounted(() => {
  disconnect()
})
</script>
