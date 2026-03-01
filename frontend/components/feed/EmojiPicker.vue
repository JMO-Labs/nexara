<!--
  @file components/feed/EmojiPicker.vue
  @brief Categorized emoji picker popover for reactions.

  Displays a grid of emojis organized by category. Users can browse
  categories or scroll through all emojis. Emits a `select` event
  when an emoji is clicked.
-->
<template>
  <div
    data-testid="emoji-picker"
    class="w-64 rounded-lg border border-border bg-popover p-2 shadow-lg"
    @click.stop
  >
    <!-- Category tabs -->
    <div class="mb-2 flex gap-1 border-b border-border pb-1">
      <button
        v-for="cat in categories"
        :key="cat.name"
        type="button"
        :class="[
          'rounded px-1.5 py-0.5 text-sm transition-colors',
          activeCategory === cat.name
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-accent',
        ]"
        :aria-label="cat.name"
        @click="activeCategory = cat.name"
      >
        {{ cat.icon }}
      </button>
    </div>

    <!-- Emoji grid -->
    <div
      data-testid="emoji-grid"
      class="grid max-h-48 grid-cols-7 gap-0.5 overflow-y-auto"
    >
      <button
        v-for="emoji in activeEmojis"
        :key="emoji"
        type="button"
        class="emoji-btn flex h-8 w-8 items-center justify-center rounded text-lg transition-colors hover:bg-accent"
        :aria-label="`React with ${emoji}`"
        @click="$emit('select', emoji)"
      >
        {{ emoji }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief EmojiPicker component with categorized emoji grid.
 */
import { ref, computed } from "vue";

defineEmits<{
  /** @brief Emitted when an emoji is clicked. */
  (e: "select", emoji: string): void;
}>();

/** @brief Emoji category definition. */
interface EmojiCategory {
  name: string;
  icon: string;
  emojis: string[];
}

/** @brief Available emoji categories with their emoji sets. */
const categories: EmojiCategory[] = [
  {
    name: "Smileys",
    icon: "😀",
    emojis: [
      "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂",
      "🙂", "😊", "😇", "🥰", "😍", "🤩", "😘", "😋",
      "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "😏",
      "😐", "😑", "😶", "😒", "🙄", "😬", "😮‍💨", "🤥",
      "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕",
      "🤢", "🤮", "🥵", "🥶", "🥴", "😵", "🤯", "🤠",
    ],
  },
  {
    name: "Gestures",
    icon: "👍",
    emojis: [
      "👍", "👎", "👏", "🙌", "🤝", "🙏", "✌️", "🤞",
      "🤟", "🤘", "👌", "🤌", "👈", "👉", "👆", "👇",
      "☝️", "✋", "🤚", "🖐️", "🖖", "👋", "🤙", "💪",
      "🦾", "🖕", "✍️", "🤳", "💅", "🦵", "🦶", "👂",
    ],
  },
  {
    name: "Hearts",
    icon: "❤️",
    emojis: [
      "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍",
      "🤎", "💔", "❤️‍🔥", "❤️‍🩹", "💕", "💞", "💓", "💗",
      "💖", "💝", "💘", "💌", "💟", "♥️", "🫶", "🫀",
    ],
  },
  {
    name: "Objects",
    icon: "🔥",
    emojis: [
      "🔥", "⭐", "🌟", "✨", "💫", "🎉", "🎊", "🏆",
      "🥇", "🥈", "🥉", "🎯", "💯", "💡", "🔔", "🎵",
      "🎶", "📣", "💰", "💎", "🧲", "🔮", "🪄", "🎪",
      "🎭", "🖼️", "🧩", "🎲", "🪁", "📌", "📎", "🔑",
    ],
  },
  {
    name: "Nature",
    icon: "🌿",
    emojis: [
      "🌿", "🍀", "🌸", "🌺", "🌻", "🌹", "🌷", "🌱",
      "🌲", "🌳", "🌴", "🌵", "🍁", "🍂", "🍃", "🌊",
      "☀️", "🌙", "⭐", "🌈", "☁️", "⛅", "🌤️", "❄️",
      "🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🐨",
    ],
  },
  {
    name: "Food",
    icon: "🍕",
    emojis: [
      "🍕", "🍔", "🍟", "🌭", "🍿", "🧁", "🍰", "🎂",
      "🍩", "🍪", "🍫", "🍬", "🍭", "☕", "🍵", "🧃",
      "🥤", "🍺", "🍷", "🥂", "🍾", "🧊", "🍎", "🍊",
      "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🥝", "🍑",
    ],
  },
];

/** @brief Currently selected category. */
const activeCategory = ref(categories[0].name);

/** @brief Emojis for the currently active category. */
const activeEmojis = computed(
  () => categories.find((c) => c.name === activeCategory.value)?.emojis ?? [],
);
</script>
