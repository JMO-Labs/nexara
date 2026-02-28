<!--
  @file components/feed/ReactionBar.vue
  @brief Emoji reaction display and toggle component.

  Renders a row of reaction buttons with counts. Highlights reactions
  the current user has selected. Emits a `react` event when clicked
  to trigger optimistic updates in the feed store.
-->
<template>
  <div
    class="flex flex-wrap items-center gap-1"
    role="group"
    :aria-label="$t('feed.reactions')"
  >
    <button
      v-for="reaction in reactions"
      :key="reaction.emoji"
      :data-testid="`reaction-${reaction.emoji}`"
      :class="[
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-sm',
        'border transition-colors duration-150 cursor-pointer',
        'hover:bg-accent',
        'focus:outline-none focus:ring-2 focus:ring-ring',
        reaction.reacted_by_me
          ? 'reaction-active border-primary bg-primary/10'
          : 'border-border',
      ]"
      :aria-label="`${reaction.emoji} ${reaction.count} reactions`"
      :aria-pressed="reaction.reacted_by_me"
      @click="$emit('react', postId, reaction.emoji)"
    >
      <span>{{ reaction.emoji }}</span>
      <span class="text-xs font-medium text-muted-foreground">{{
        reaction.count
      }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief ReactionBar component props and events.
 */
import type { Reaction } from "~/types/api";

defineProps<{
  /** @brief List of reactions to display. */
  reactions: Reaction[];
  /** @brief ID of the post these reactions belong to. */
  postId: string;
}>();

defineEmits<{
  /** @brief Emitted when a user clicks a reaction. */
  (e: "react", postId: string, emoji: string): void;
}>();
</script>
