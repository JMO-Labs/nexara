<!--
  @file components/feed/PostActions.vue
  @brief Kebab-menu dropdown with edit and delete actions for a post.

  Appears only for the post author or admins. Closes on click-outside
  or Escape.
-->
<template>
  <div ref="menuRef" class="relative">
    <button
      class="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      :aria-label="$t('feed.editPost')"
      :aria-expanded="open"
      aria-haspopup="true"
      @click.stop="open = !open"
    >
      <EllipsisVerticalIcon class="h-5 w-5" />
    </button>

    <Transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="scale-95 opacity-0"
      enter-to-class="scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="scale-100 opacity-100"
      leave-to-class="scale-95 opacity-0"
    >
      <div
        v-if="open"
        class="absolute right-0 top-full z-40 mt-1 w-36 origin-top-right rounded-lg border border-border bg-popover p-1 shadow-lg"
        role="menu"
        @keydown.escape="open = false"
      >
        <button
          class="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-accent"
          role="menuitem"
          @click="handleEdit"
        >
          <PencilSquareIcon class="h-4 w-4 text-muted-foreground" />
          {{ $t("feed.editPost") }}
        </button>
        <button
          class="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-sm text-destructive transition-colors hover:bg-destructive/10"
          role="menuitem"
          @click="handleDelete"
        >
          <TrashIcon class="h-4 w-4" />
          {{ $t("feed.deletePost") }}
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief PostActions dropdown menu with click-outside closing.
 */
import { ref, onMounted, onBeforeUnmount } from "vue";
import {
  EllipsisVerticalIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";

const emit = defineEmits<{
  (e: "edit" | "delete"): void;
}>();

const open = ref(false);
const menuRef = ref<HTMLElement | null>(null);

function handleEdit(): void {
  open.value = false;
  emit("edit");
}

function handleDelete(): void {
  open.value = false;
  emit("delete");
}

function onClickOutside(event: MouseEvent): void {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener("mousedown", onClickOutside));
onBeforeUnmount(() => document.removeEventListener("mousedown", onClickOutside));
</script>
