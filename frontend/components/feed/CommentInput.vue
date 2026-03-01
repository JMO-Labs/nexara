<!--
  @file components/feed/CommentInput.vue
  @brief Comment/reply input with plus-menu for reactions and media.

  Layout: [text input] [+ button] [submit button]

  The "+" button opens a floating popover with two options:
  - Reactions: hover reveals quick-react emoji presets plus a "more"
    button that opens the full emoji picker.
  - Media: disabled stub for future media-comment support.

  Used in CommentThread (post-level) and CommentNode (reply-level).
-->
<template>
  <form
    data-testid="comment-form"
    class="flex items-center gap-1.5"
    @submit.prevent="handleSubmit"
  >
    <input
      ref="inputRef"
      v-model="text"
      data-testid="comment-input"
      type="text"
      :placeholder="placeholder"
      :aria-label="placeholder"
      class="flex-1 rounded-md border border-input bg-muted px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
    >

    <!-- Plus button wrapper — positions all menus over the "+" -->
    <div class="relative">
      <!-- Plus menu trigger -->
      <button
        type="button"
        data-testid="plus-menu-trigger"
        aria-label="Attach"
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        @click.stop="menuOpen = !menuOpen"
      >
        +
      </button>

      <!-- Plus menu popover -->
      <div
        v-if="menuOpen"
        data-testid="plus-menu"
        class="absolute bottom-full left-1/2 z-50 mb-1 -translate-x-1/2 flex items-center gap-0.5 rounded-full border border-border bg-popover px-1 py-0.5 shadow-lg"
        @click.stop
      >
        <!-- Reactions option with hover submenu -->
        <div class="relative pb-0" @mouseleave="reactionsHover = false">
          <button
            type="button"
            data-testid="plus-menu-reactions"
            class="flex items-center justify-center rounded-md p-1.5 text-lg transition-colors hover:bg-accent"
            aria-label="Reactions"
            @mouseenter="reactionsHover = true"
          >
            😀
          </button>

          <!-- Quick reactions submenu -->
          <div
            v-if="reactionsHover"
            data-testid="reactions-submenu"
            class="absolute bottom-full left-1/2 -translate-x-1/2 flex items-center gap-0.5 rounded-full border border-border bg-popover px-1.5 py-1 shadow-lg"
          >
            <button
              v-for="emoji in quickEmojis"
              :key="emoji"
              type="button"
              :data-testid="`quick-react-${emoji}`"
              class="flex h-7 w-7 items-center justify-center rounded-full text-base transition-transform hover:scale-125 hover:bg-accent"
              :aria-label="`React with ${emoji}`"
              @click.stop="onQuickReact(emoji)"
            >
              {{ emoji }}
            </button>

            <!-- More emojis button -->
            <button
              type="button"
              data-testid="reactions-more"
              class="flex h-7 w-7 items-center justify-center rounded-full text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="More reactions"
              @click.stop="pickerOpen = true"
            >
              +
            </button>
          </div>
        </div>

        <!-- Media option (stub) -->
        <button
          type="button"
          data-testid="plus-menu-media"
          disabled
          class="flex items-center justify-center rounded-md p-1.5 text-lg opacity-50 cursor-not-allowed"
          aria-label="Attach media"
          title="Coming soon"
        >
          📎
        </button>
      </div>

      <!-- Full emoji picker -->
      <div
        v-if="pickerOpen"
        class="absolute bottom-full right-0 z-50 mb-1"
        @click.stop
      >
        <EmojiPicker @select="onPickerSelect" />
      </div>
    </div>

    <!-- Submit -->
    <button
      type="submit"
      data-testid="comment-submit"
      :disabled="!text.trim()"
      class="shrink-0 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
    >
      {{ submitLabel }}
    </button>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief CommentInput — unified input with plus-menu for reactions and media.
 *
 * Emits:
 * - submit(text) when the user submits text
 * - react(emoji) when the user selects a reaction emoji
 */
import { ref } from "vue";
import EmojiPicker from "~/components/feed/EmojiPicker.vue";

/** @brief Quick-reaction preset emojis. */
const quickEmojis = ["👍", "❤️", "😂", "😮", "😢", "🔥"];

withDefaults(
  defineProps<{
    /** @brief Placeholder text for the input field. */
    placeholder?: string;
    /** @brief Label for the submit button. */
    submitLabel?: string;
  }>(),
  {
    placeholder: "Add a comment...",
    submitLabel: "Send",
  },
);

const emit = defineEmits<{
  /** @brief Emitted when user submits text content or selects a reaction emoji. */
  (e: "submit" | "react", value: string): void;
}>();

/** @brief Current text input value. */
const text = ref("");

/** @brief Reference to the text input element. */
const inputRef = ref<HTMLInputElement | null>(null);

/** @brief Whether the plus-menu popover is open. */
const menuOpen = ref(false);

/** @brief Whether the reactions option is being hovered. */
const reactionsHover = ref(false);

/** @brief Whether the full emoji picker is open. */
const pickerOpen = ref(false);

/**
 * @brief Handle form submission.
 *
 * Emits submit with trimmed text and clears the input.
 */
function handleSubmit(): void {
  const trimmed = text.value.trim();
  if (!trimmed) return;
  emit("submit", trimmed);
  text.value = "";
}

/**
 * @brief Handle quick-react emoji click.
 * @param emoji Selected emoji string.
 */
function onQuickReact(emoji: string): void {
  emit("react", emoji);
  closeAllMenus();
}

/**
 * @brief Handle emoji selection from the full picker.
 * @param emoji Selected emoji string.
 */
function onPickerSelect(emoji: string): void {
  emit("react", emoji);
  closeAllMenus();
}

/** @brief Close all menus and submenus. */
function closeAllMenus(): void {
  menuOpen.value = false;
  reactionsHover.value = false;
  pickerOpen.value = false;
}

/** @brief Focus the text input programmatically. */
function focus(): void {
  inputRef.value?.focus();
}

defineExpose({ focus });
</script>
