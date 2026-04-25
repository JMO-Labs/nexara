<!--
  @file components/chat/MessageList.vue
  @brief Scrollable chat message list with load-older and live region.

  Renders messages newest-first from the store. Provides a Load
  Older button when more history is available. A visually-hidden
  ARIA live region announces new incoming messages to assistive tech.
-->
<template>
  <div
    ref="scrollRoot"
    class="flex h-full flex-col-reverse overflow-y-auto"
    data-testid="chat-message-list"
    role="log"
    aria-live="polite"
    aria-relevant="additions"
    :aria-label="$t('chat.messagesLive')"
  >
    <!-- Reversed column — messages render newest first visually -->
    <div class="flex flex-col-reverse gap-1 p-3">
      <MessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
        :current-user-id="currentUserId"
        :is-admin="isAdmin"
        @edit="(id, content) => $emit('edit', id, content)"
        @delete="(id) => $emit('delete', id)"
      />

      <!-- Empty state -->
      <p
        v-if="!loading && messages.length === 0"
        class="py-10 text-center text-sm text-muted-foreground"
        data-testid="chat-empty"
      >
        {{ $t("chat.noMessages") }}
      </p>

      <!-- Load older trigger -->
      <div v-if="hasMore" class="flex justify-center pt-2">
        <button
          type="button"
          :disabled="loading"
          class="rounded-md border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent disabled:opacity-50"
          data-testid="chat-load-older"
          @click="$emit('loadOlder')"
        >
          {{ loading ? $t("chat.loading") : $t("chat.loadOlder") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief MessageList - scrollable channel message list.
 */
import { ref } from "vue";
import MessageItem from "~/components/chat/MessageItem.vue";
import type { ChatMessage } from "~/types/api";

defineProps<{
  /** @brief Messages ordered newest-first. */
  messages: ChatMessage[];
  /** @brief Whether older pages exist. */
  hasMore: boolean;
  /** @brief Whether a fetch is in progress. */
  loading: boolean;
  /** @brief Current user id for author controls. */
  currentUserId?: string | null;
  /** @brief Admin flag. */
  isAdmin?: boolean;
}>();

defineEmits<{
  (e: "loadOlder"): void;
  (e: "edit", id: string, content: string): void;
  (e: "delete", id: string): void;
}>();

const scrollRoot = ref<HTMLElement | null>(null);
</script>
