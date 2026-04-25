<!--
  @file components/chat/MessageInput.vue
  @brief Chat composer with Enter-to-send and throttled typing indicator.

  Enter sends the message, Shift+Enter inserts a newline. Typing events
  are emitted on input at most once every 2 seconds. Controlled via
  `disabled` prop when the socket is down.
-->
<template>
  <form
    class="flex items-end gap-2 border-t border-border bg-background p-3"
    data-testid="chat-input-form"
    @submit.prevent="handleSubmit"
  >
    <label class="sr-only" :for="textareaId">{{ $t("chat.placeholder") }}</label>
    <textarea
      :id="textareaId"
      ref="textareaEl"
      v-model="content"
      :placeholder="$t('chat.placeholder')"
      :aria-label="$t('chat.placeholder')"
      :disabled="disabled"
      rows="1"
      class="min-h-9 max-h-40 flex-1 resize-none rounded-md border border-input bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      data-testid="chat-input"
      @keydown.enter.exact.prevent="handleEnter"
      @input="handleInput"
    />
    <button
      type="submit"
      :disabled="disabled || !content.trim()"
      class="h-9 shrink-0 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      data-testid="chat-input-send"
      :aria-label="$t('chat.send')"
    >
      {{ $t("chat.send") }}
    </button>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief MessageInput — chat composer with Enter-to-send.
 */
import { ref } from "vue";

const props = defineProps<{
  /** @brief Disable input when socket is closed. */
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: "send", content: string): void;
  (e: "typing"): void;
}>();

/** @brief Minimum delay between typing events in ms. */
const TYPING_THROTTLE_MS = 2_000;

const content = ref("");
const textareaEl = ref<HTMLTextAreaElement | null>(null);
const textareaId = `chat-input-${Math.random().toString(36).slice(2, 8)}`;
let lastTypingAt = 0;

/** @brief Emit a typing event at most once per TYPING_THROTTLE_MS. */
function handleInput(): void {
  if (props.disabled) return;
  if (!content.value.trim()) return;
  const now = Date.now();
  if (now - lastTypingAt >= TYPING_THROTTLE_MS) {
    lastTypingAt = now;
    emit("typing");
  }
}

/** @brief Send on bare Enter; Shift+Enter handled by textarea default. */
function handleEnter(event: KeyboardEvent): void {
  if (event.shiftKey) return;
  handleSubmit();
}

/** @brief Submit the message and clear the field. */
function handleSubmit(): void {
  const trimmed = content.value.trim();
  if (!trimmed || props.disabled) return;
  emit("send", trimmed);
  content.value = "";
  lastTypingAt = 0;
}
</script>
