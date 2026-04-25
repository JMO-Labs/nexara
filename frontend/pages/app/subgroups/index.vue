<!--
  @file pages/app/subgroups/index.vue
  @brief Subgroup directory page with list and create modal.

  Lists all subgroups visible to the current user via the subgroups
  Pinia store. Authenticated users can open a Create Subgroup modal to
  register a new subgroup. Slug inputs are validated client-side so the
  UX matches the backend's regex constraint.
-->
<template>
  <div class="space-y-6">
    <div
      class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ $t("subgroups.directoryTitle") }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ $t("subgroups.title") }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <input
          v-model="searchQuery"
          type="search"
          :placeholder="$t('common.search')"
          data-testid="subgroups-search"
          class="max-w-xs rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring"
        />
        <button
          type="button"
          data-testid="subgroups-create-button"
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
          @click="openCreate"
        >
          {{ $t("subgroups.create") }}
        </button>
      </div>
    </div>

    <div
      v-if="subgroupsStore.loading && subgroupsStore.list.length === 0"
      class="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground"
      data-testid="subgroups-loading"
    >
      {{ $t("common.loading") }}
    </div>

    <div
      v-else-if="filteredList.length === 0"
      class="rounded-lg border border-dashed border-border bg-card p-8 text-center text-muted-foreground"
      data-testid="subgroups-empty"
    >
      {{ $t("subgroups.directoryEmpty") }}
    </div>

    <div
      v-else
      data-testid="subgroups-grid"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <SubgroupCard
        v-for="sg in filteredList"
        :key="sg.id"
        :subgroup="sg"
      />
    </div>

    <!-- Create modal -->
    <Teleport v-if="showCreate" to="body">
      <div
        class="fixed inset-0 z-[9998] flex items-center justify-center bg-black/50 p-4"
        data-testid="subgroups-create-modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="createModalTitleId"
        @click.self="closeCreate"
        @keydown.esc="closeCreate"
      >
        <div
          class="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl"
        >
          <h2
            :id="createModalTitleId"
            class="mb-4 text-lg font-semibold text-foreground"
          >
            {{ $t("subgroups.createTitle") }}
          </h2>
          <form class="space-y-4" @submit.prevent="handleCreate">
            <div>
              <label
                for="sg_name"
                class="mb-1 block text-sm font-medium text-foreground"
              >
                {{ $t("subgroups.name") }}
              </label>
              <input
                id="sg_name"
                ref="firstFieldRef"
                v-model="createForm.name"
                type="text"
                required
                maxlength="120"
                data-testid="subgroups-create-name"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label
                for="sg_slug"
                class="mb-1 block text-sm font-medium text-foreground"
              >
                {{ $t("subgroups.slug") }}
              </label>
              <input
                id="sg_slug"
                v-model="createForm.slug"
                type="text"
                required
                minlength="2"
                maxlength="80"
                pattern="^[a-z0-9][a-z0-9_-]*$"
                data-testid="subgroups-create-slug"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
              />
              <p class="mt-1 text-xs text-muted-foreground">
                {{ $t("subgroups.slugHint") }}
              </p>
            </div>
            <div>
              <label
                for="sg_description"
                class="mb-1 block text-sm font-medium text-foreground"
              >
                {{ $t("subgroups.description") }}
              </label>
              <textarea
                id="sg_description"
                v-model="createForm.description"
                rows="3"
                maxlength="2000"
                data-testid="subgroups-create-description"
                class="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label
                for="sg_policy"
                class="mb-1 block text-sm font-medium text-foreground"
              >
                {{ $t("subgroups.joinPolicy") }}
              </label>
              <select
                id="sg_policy"
                v-model="createForm.join_policy"
                data-testid="subgroups-create-policy"
                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
              >
                <option value="open">
                  {{ $t("subgroups.policy.open") }}
                </option>
                <option value="invite_only">
                  {{ $t("subgroups.policy.invite_only") }}
                </option>
                <option value="admin_approval">
                  {{ $t("subgroups.policy.admin_approval") }}
                </option>
              </select>
            </div>
            <label class="flex items-center gap-2 text-sm text-foreground">
              <input
                v-model="createForm.is_private"
                type="checkbox"
                data-testid="subgroups-create-private"
                class="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
              <span>{{ $t("subgroups.isPrivate") }}</span>
            </label>

            <p
              v-if="createError"
              class="text-sm text-red-600 dark:text-red-400"
              data-testid="subgroups-create-error"
            >
              {{ createError }}
            </p>

            <div class="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                class="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                @click="closeCreate"
              >
                {{ $t("common.cancel") }}
              </button>
              <button
                type="submit"
                :disabled="creating"
                data-testid="subgroups-create-submit"
                class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {{ creating ? $t("common.loading") : $t("subgroups.create") }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Subgroup directory page with a create modal.
 *
 * Uses the subgroups store for both list display and create action. The
 * create modal performs basic client-side validation that mirrors the
 * backend Pydantic schema so the submit button does not round-trip
 * obviously invalid payloads.
 */
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useSubgroupsStore } from "~/stores/subgroups";
import { useUiStore } from "~/stores/ui";
import SubgroupCard from "~/components/subgroups/SubgroupCard.vue";
import type { JoinPolicy, SubgroupCreatePayload } from "~/types/api";

const subgroupsStore = useSubgroupsStore();
const uiStore = useUiStore();
const router = useRouter();
const { t: $t } = useI18n();

const searchQuery = ref("");
const showCreate = ref(false);
const creating = ref(false);
const createError = ref<string | null>(null);
const firstFieldRef = ref<HTMLInputElement | null>(null);
const createModalTitleId = "subgroups-create-title";

const createForm = reactive<{
  name: string;
  slug: string;
  description: string;
  is_private: boolean;
  join_policy: JoinPolicy;
}>({
  name: "",
  slug: "",
  description: "",
  is_private: false,
  join_policy: "open",
});

const SLUG_REGEX = /^[a-z0-9][a-z0-9_-]*$/;

/** @brief Filter the directory list with a simple case-insensitive match. */
const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return subgroupsStore.list;
  return subgroupsStore.list.filter(
    (s) =>
      s.name.toLowerCase().includes(q) ||
      s.slug.toLowerCase().includes(q) ||
      (s.description ?? "").toLowerCase().includes(q),
  );
});

/** @brief Open the create modal and focus the first field on next tick. */
function openCreate(): void {
  resetCreateForm();
  showCreate.value = true;
  nextTick(() => firstFieldRef.value?.focus());
}

/** @brief Close the create modal and clear validation state. */
function closeCreate(): void {
  showCreate.value = false;
  createError.value = null;
}

/** @brief Reset the create form fields to defaults. */
function resetCreateForm(): void {
  createForm.name = "";
  createForm.slug = "";
  createForm.description = "";
  createForm.is_private = false;
  createForm.join_policy = "open";
  createError.value = null;
}

/** @brief Submit handler for the create form. */
async function handleCreate(): Promise<void> {
  createError.value = null;
  if (!createForm.name.trim()) {
    createError.value = $t("subgroups.errors.nameRequired");
    return;
  }
  if (!SLUG_REGEX.test(createForm.slug)) {
    createError.value = $t("subgroups.errors.slugInvalid");
    return;
  }

  creating.value = true;
  try {
    const payload: SubgroupCreatePayload = {
      name: createForm.name.trim(),
      slug: createForm.slug.trim(),
      description: createForm.description.trim() || null,
      is_private: createForm.is_private,
      join_policy: createForm.join_policy,
    };
    const created = await subgroupsStore.createSubgroup(payload);
    uiStore.showToast({
      type: "success",
      message: $t("subgroups.created"),
    });
    closeCreate();
    await router.push(`/app/subgroups/${created.slug}`);
  } catch (err) {
    createError.value = err instanceof Error ? err.message : $t("common.error");
  } finally {
    creating.value = false;
  }
}

onMounted(async () => {
  try {
    await subgroupsStore.fetchList();
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  }
});
</script>
