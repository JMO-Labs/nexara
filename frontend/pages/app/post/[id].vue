<!--
  @file pages/app/post/[id].vue
  @brief Single post detail page with full comment thread.

  Displays a single post with its complete comment thread and
  allows adding new comments and reactions.
-->
<template>
  <div class="space-y-4">
    <NuxtLink to="/app" class="text-sm text-primary hover:underline">
      &larr; {{ $t('feed.title') }}
    </NuxtLink>

    <LoadingSpinner v-if="loading" size="lg" />

    <template v-if="post">
      <PostCard :post="post" @react="handleReaction" />

      <div class="rounded-lg border border-border bg-card p-4">
        <h2 class="mb-4 text-lg font-semibold text-card-foreground">
          {{ $t('feed.comments') }} ({{ post.comment_count }})
        </h2>
        <CommentThread
          :comments="comments"
          :post-id="post.id"
          @add-comment="handleAddComment"
        />
      </div>
    </template>

    <div v-if="error" class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Post detail page with comments loading.
 */
import { ref, onMounted } from 'vue'
import { useApi } from '~/composables/useApi'
import PostCard from '~/components/feed/PostCard.vue'
import CommentThread from '~/components/feed/CommentThread.vue'
import LoadingSpinner from '~/components/common/LoadingSpinner.vue'
import type { Post, Comment } from '~/types/api'

const props = defineProps<{ id: string }>()

const api = useApi()
const post = ref<Post | null>(null)
const comments = ref<Comment[]>([])
const loading = ref(true)
const error = ref('')

function handleReaction(_postId: string, emoji: string): void {
  if (!post.value) return
  const existing = post.value.reactions.find(r => r.emoji === emoji)
  if (existing) {
    existing.reacted_by_me = !existing.reacted_by_me
    existing.count += existing.reacted_by_me ? 1 : -1
  } else {
    post.value.reactions.push({ emoji, count: 1, reacted_by_me: true })
  }
}

async function handleAddComment(payload: { postId: string; content: string; parentId: string | null }): Promise<void> {
  try {
    const newComment = await api.post<Comment>(`/posts/${payload.postId}/comments`, {
      content: payload.content,
      parent_id: payload.parentId,
    })
    comments.value.push(newComment)
    if (post.value) post.value.comment_count++
  } catch {
    /* Toast handled by global error handler */
  }
}

onMounted(async () => {
  try {
    const routeId = props.id || (typeof window !== 'undefined' ? window.location.pathname.split('/').pop() : '')
    post.value = await api.get<Post>(`/posts/${routeId}`)
    comments.value = await api.get<Comment[]>(`/posts/${routeId}/comments`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load post'
  } finally {
    loading.value = false
  }
})
</script>
