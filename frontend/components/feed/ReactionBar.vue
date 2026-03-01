<!--
  @file components/feed/ReactionBar.vue
  @brief Display-only emoji reaction badges with counts.

  Shows existing reactions as compact pills with emoji and count.
  Clicking a badge toggles the reaction (emits "react"). No inline
  quick-react presets or picker — reaction input is handled by the
  CommentInput plus-menu instead.
-->
<template>
  <div
    v-if="reactions.length"
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
      @click.stop="$emit('react', targetType, targetId, reaction.emoji)"
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
 * @brief Display-only ReactionBar component props and events.
 *
 * Generic reaction badges supporting posts, comments, and media targets.
 * Clicking an existing badge toggles the user's reaction via the react event.
 */
import type { Reaction } from "~/types/api";

defineProps<{
  /** @brief List of existing reactions to display. */
  reactions: Reaction[];
  /** @brief Target entity type for the reaction. */
  targetType: "post" | "comment" | "media";
  /** @brief ID of the target entity. */
  targetId: string;
}>();

defineEmits<{
  /** @brief Emitted when a user clicks a reaction badge to toggle it. */
  (e: "react", targetType: string, targetId: string, emoji: string): void;
}>();
</script>
