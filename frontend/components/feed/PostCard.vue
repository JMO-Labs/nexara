<!--
  @file components/feed/PostCard.vue
  @brief Post display card with content, media, reactions, and comments.

  Renders a single post in the activity feed. Content is Markdown-rendered
  and sanitized. Uses the shadcn-inspired card token system.
-->
<template>
  <article class="rounded-lg border border-border bg-card p-4 shadow-sm">
    <!-- Author header -->
    <div class="mb-3 flex items-center gap-3">
      <div
        class="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground"
        :aria-label="post.author.display_name"
      >
        {{ post.author.display_name.charAt(0).toUpperCase() }}
      </div>
      <div>
        <p class="font-semibold text-card-foreground">{{ post.author.display_name }}</p>
        <p class="text-xs text-muted-foreground">@{{ post.author.username }} &middot; {{ timeAgo(post.created_at) }}</p>
      </div>
    </div>

    <!-- Post content (Markdown rendered) -->
    <div
      data-testid="post-content"
      class="prose prose-sm max-w-none dark:prose-invert mb-3"
      v-html="renderedContent"
    />

    <!-- Media grid -->
    <div v-if="post.media.length" class="mb-3 grid gap-2" :class="mediaGridClass">
      <img
        v-for="media in post.media"
        :key="media.id"
        data-testid="media-thumbnail"
        :src="media.thumbnail_url || media.url"
        :alt="$t('feed.attachMedia')"
        :width="media.width || undefined"
        :height="media.height || undefined"
        class="rounded-lg object-cover w-full"
        loading="lazy"
      />
    </div>

    <!-- Reactions -->
    <ReactionBar
      :reactions="post.reactions"
      :post-id="post.id"
      @react="(postId: string, emoji: string) => $emit('react', postId, emoji)"
    />

    <!-- Comment count -->
    <div class="mt-2 text-sm text-muted-foreground">
      <span>{{ post.comment_count }} {{ $t('feed.comments') }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
/**
 * @brief PostCard component props, events, and computed state.
 */
import { computed } from 'vue'
import type { Post } from '~/types/api'
import { renderMarkdown } from '~/utils/markdown'
import { timeAgo } from '~/utils/date'
import ReactionBar from '~/components/feed/ReactionBar.vue'

const props = defineProps<{
  /** @brief The post to render. */
  post: Post
}>()

defineEmits<{
  (e: 'react', postId: string, emoji: string): void
}>()

/** @brief Markdown content rendered to sanitized HTML. */
const renderedContent = computed(() => renderMarkdown(props.post.content))

/** @brief CSS grid class based on number of media attachments. */
const mediaGridClass = computed(() => {
  const count = props.post.media.length
  if (count === 1) return 'grid-cols-1'
  if (count === 2) return 'grid-cols-2'
  return 'grid-cols-2 sm:grid-cols-3'
})
</script>
