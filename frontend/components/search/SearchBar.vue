<!--
  @file components/search/SearchBar.vue
  @brief Search input with debounce and submit navigation.

  Debounces input (300ms). On Enter, navigates to /app/search?q=...
-->
<template>
  <form
    class="flex items-center gap-2"
    role="search"
    @submit.prevent="handleSubmit"
  >
    <label for="search-input" class="sr-only">{{
      $t("search.placeholder")
    }}</label>
    <input
      id="search-input"
      ref="inputRef"
      v-model="localValue"
      type="search"
      class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
      aria-label="Search"
      :placeholder="$t('search.placeholder')"
      autocomplete="off"
    >
    <button
      type="submit"
      class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
    >
      {{ $t("common.search") }}
    </button>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief SearchBar with debounced input and submit-to-navigate.
 */
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

const props = withDefaults(
  defineProps<{
    /** @brief Controlled search value (optional). */
    modelValue?: string;
  }>(),
  { modelValue: "" },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const router = useRouter();
const inputRef = ref<HTMLInputElement | null>(null);
const localValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (v) => {
    localValue.value = v;
  },
);

/** @brief Debounce emit by 300ms to avoid excessive updates while typing. */
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
watch(localValue, (v) => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    emit("update:modelValue", v);
    debounceTimer = null;
  }, 300);
});

/**
 * @brief Navigate to search page on form submit.
 */
function handleSubmit(): void {
  const q = (localValue.value || "").trim();
  if (q.length >= 2) {
    router.push({ path: "/app/search", query: { q } });
  }
}
</script>
