<!--
  @file components/profile/InterestTagInput.vue
  @brief Autocomplete tag input for adding interests.
-->
<template>
  <form
    data-testid="interest-add"
    class="flex flex-wrap items-end gap-2"
    @submit.prevent="handleSubmit"
  >
    <div class="flex-1 min-w-[120px]">
      <label for="interest-category" class="sr-only">
        {{ $t("profile.interests.category") }}
      </label>
      <select
        id="interest-category"
        v-model="selectedCategory"
        class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
      >
        <option value="" disabled>
          {{ $t("profile.interests.selectCategory") }}
        </option>
        <option
          v-for="cat in sortedCategories"
          :key="cat.slug"
          :value="cat.slug"
        >
          {{ cat.label }}
        </option>
      </select>
    </div>
    <div class="flex-1 min-w-[120px]">
      <label for="interest-value" class="sr-only">
        {{ $t("profile.interests.value") }}
      </label>
      <input
        id="interest-value"
        v-model="value"
        type="text"
        :placeholder="$t('profile.interests.valuePlaceholder')"
        class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
      >
    </div>
    <button
      type="submit"
      :disabled="!canSubmit"
      class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:ring-2 focus:ring-ring disabled:opacity-50"
    >
      {{ $t("profile.interests.add") }}
    </button>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief Autocomplete tag input for adding interests.
 */
import { ref, computed } from "vue";
import type { InterestCategory } from "~/types/api";

const props = defineProps<{
  categories: InterestCategory[];
}>();

const emit = defineEmits<{
  add: [categorySlug: string, value: string];
}>();

const selectedCategory = ref("");
const value = ref("");

const sortedCategories = computed(() =>
  [...props.categories].sort((a, b) => a.sort_order - b.sort_order),
);

const canSubmit = computed(
  () => !!selectedCategory.value && !!value.value.trim(),
);

function handleSubmit(): void {
  const cat = selectedCategory.value;
  const val = value.value.trim();
  if (!cat || !val) return;
  emit("add", cat, val);
  value.value = "";
}
</script>
