<!--
  @file components/chat/MessageItem.vue
  @brief Single chat message with author, timestamp, edit/delete, link preview.

  Displays one message in a channel. Own messages gain inline edit and
  delete actions. Deleted tombstones render muted. URLs in the message
  body are surfaced through an inline LinkPreviewCard when a `preview`
  prop is provided.
-->
<template>
  <div
    class="group flex gap-2 rounded-md px-2 py-1.5 hover:bg-accent/40"
    :data-testid="`chat-message-${message.id}`"
    role="article"
    :aria-label="ariaLabel"
  >
    <!-- Avatar -->
    <div
      class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground"
      :aria-hidden="true"
    >
      {{ initials }}
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-baseline gap-2">
        <span class="truncate text-sm font-semibold text-card-foreground">
          {{ authorName }}
        </span>
        <span
          class="text-xs text-muted-foreground"
          :title="message.created_at"
        >
          {{ timeAgo(message.created_at) }}
        </span>
        <span
          v-if="message.edited_at && !message.deleted"
          class="text-xs italic text-muted-foreground"
          data-testid="chat-message-edited"
        >
          ({{ $t("chat.edited") }})
        </span>
      </div>

      <!-- Inline edit mode -->
      <div v-if="editing" class="mt-1">
        <textarea
          v-model="editContent"
          class="w-full resize-none rounded-md border border-input bg-muted p-2 text-sm text-foreground focus:ring-2 focus:ring-ring"
          rows="2"
          data-testid="chat-message-edit-input"
          :aria-label="$t('chat.edit')"
          @keydown.enter.exact.prevent="saveEdit"
          @keydown.esc.prevent="cancelEdit"
        />
        <div class="mt-1 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
            data-testid="chat-message-edit-cancel"
            @click="cancelEdit"
          >
            {{ $t("chat.cancel") }}
          </button>
          <button
            type="button"
            :disabled="!editContent.trim()"
            class="rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="chat-message-edit-save"
            @click="saveEdit"
          >
            {{ $t("chat.save") }}
          </button>
        </div>
      </div>

      <!-- Rendered body -->
      <p
        v-else
        class="whitespace-pre-wrap break-words text-sm"
        :class="message.deleted ? 'italic text-muted-foreground' : 'text-foreground'"
        data-testid="chat-message-content"
      >
        {{ message.content }}
      </p>

      <!-- Inline link preview -->
      <div v-if="preview && !message.deleted" class="mt-2">
        <LinkPreviewCard :preview="preview" />
      </div>
    </div>

    <!-- Hover actions (own messages, non-deleted) -->
    <div
      v-if="canManage && !message.deleted && !editing"
      class="flex shrink-0 items-start gap-1 opacity-0 transition-opacity group-hover:opacity-100"
    >
      <button
        type="button"
        class="rounded-md p-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
        data-testid="chat-message-edit"
        :aria-label="$t('chat.edit')"
        @click="startEdit"
      >
        {{ $t("chat.edit") }}
      </button>
      <button
        type="button"
        class="rounded-md p-1 text-xs text-muted-foreground hover:bg-destructive/20 hover:text-destructive"
        data-testid="chat-message-delete"
        :aria-label="$t('chat.delete')"
        @click="onDelete"
      >
        {{ $t("chat.delete") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief MessageItem - renders a single chat message row.
 */
import { ref, computed } from "vue";
import { timeAgo } from "~/utils/date";
import LinkPreviewCard from "~/components/content/LinkPreviewCard.vue";
import type { ChatMessage, LinkPreview } from "~/types/api";

const props = defineProps<{
  /** @brief Message to display. */
  message: ChatMessage;
  /** @brief Optional link preview metadata to embed inline. */
  preview?: LinkPreview | null;
  /** @brief Current user id — drives author controls. */
  currentUserId?: string | null;
  /** @brief Whether the viewer is an admin (can delete any message). */
  isAdmin?: boolean;
}>();

const emit = defineEmits<{
  (e: "edit", id: string, content: string): void;
  (e: "delete", id: string): void;
}>();

const editing = ref(false);
const editContent = ref("");

/** @brief Whether the viewer can edit/delete this message. */
const canManage = computed(() => {
  if (!props.message.author) return false;
  if (props.isAdmin) return true;
  return props.currentUserId === props.message.author.id;
});

/** @brief Display name for the author, or "Deleted user" fallback. */
const authorName = computed(
  () => props.message.author?.display_name ?? "Unknown",
);

/** @brief Two-letter initial bubble. */
const initials = computed(() => {
  const n = authorName.value;
  return n.charAt(0).toUpperCase();
});

/** @brief Aria label used by screen readers. */
const ariaLabel = computed(
  () => `${authorName.value}: ${props.message.content}`,
);

function startEdit(): void {
  editContent.value = props.message.content;
  editing.value = true;
}

function cancelEdit(): void {
  editing.value = false;
  editContent.value = "";
}

function saveEdit(): void {
  const trimmed = editContent.value.trim();
  if (!trimmed) return;
  emit("edit", props.message.id, trimmed);
  editing.value = false;
}

function onDelete(): void {
  emit("delete", props.message.id);
}
</script>
