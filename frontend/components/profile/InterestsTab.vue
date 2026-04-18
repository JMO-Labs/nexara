<!--
  @file components/profile/InterestsTab.vue
  @brief Displays user interests grouped by category.
-->
<template>
  <div class="space-y-4">
    <div v-if="loading" class="text-muted-foreground">
      {{ $t("common.loading") }}
    </div>

    <template v-else>
      <div v-if="isOwner" data-testid="interest-add" class="mb-4">
        <ProfileInterestTagInput
          :categories="categories"
          @add="handleAdd"
        />
      </div>

      <div v-if="groupedInterests.length === 0" class="text-muted-foreground">
        {{ $t("profile.interests.empty") }}
      </div>

      <div v-else class="space-y-4">
        <section
          v-for="group in groupedInterests"
          :key="group.categorySlug"
          class="rounded-lg border border-border bg-card p-4"
        >
          <h3 class="mb-3 text-sm font-semibold text-foreground">
            {{ group.label }}
          </h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="interest in group.interests"
              :key="interest.id"
              class="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-sm text-foreground"
            >
              {{ interest.value }}
              <button
                v-if="isOwner"
                type="button"
                :aria-label="$t('profile.interests.remove')"
                class="ml-1 rounded-full p-0.5 hover:bg-destructive/20"
                @click="handleRemove(interest.id)"
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </span>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Displays user interests grouped by category.
 */
import { ref, computed, onMounted } from "vue";
import { useApi } from "~/composables/useApi";
import type {
  UserInterest,
  InterestCategory,
  UserInterestsResponse,
} from "~/types/api";

const props = defineProps<{
  userId: string;
  isOwner: boolean;
}>();

const api = useApi();
const interests = ref<UserInterest[]>([]);
const categories = ref<InterestCategory[]>([]);
const loading = ref(true);

const groupedInterests = computed(() => {
  const byCat = new Map<string, UserInterest[]>();
  for (const i of interests.value) {
    const list = byCat.get(i.category_slug) ?? [];
    list.push(i);
    byCat.set(i.category_slug, list);
  }
  const sorted = [...categories.value].sort((a, b) => a.sort_order - b.sort_order);
  return sorted
    .filter((c) => byCat.has(c.slug))
    .map((c) => ({
      categorySlug: c.slug,
      label: c.label,
      interests: byCat.get(c.slug) ?? [],
    }));
});

async function fetchInterests(): Promise<void> {
  loading.value = true;
  try {
    const res = await api.get<UserInterestsResponse>(
      `/interests/users/${props.userId}/interests`,
    );
    interests.value = res.interests ?? [];
    categories.value = res.categories ?? [];
  } catch {
    interests.value = [];
    categories.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleAdd(categorySlug: string, value: string): Promise<void> {
  try {
    await api.post(`/interests/users/${props.userId}/interests`, {
      category_slug: categorySlug,
      value,
    });
    await fetchInterests();
  } catch {
    /* Error handling could show toast */
  }
}

async function handleRemove(interestId: string): Promise<void> {
  try {
    await api.del(`/interests/users/${props.userId}/interests/${interestId}`);
    interests.value = interests.value.filter((i) => i.id !== interestId);
  } catch {
    /* Error handling could show toast */
  }
}

onMounted(fetchInterests);
</script>
