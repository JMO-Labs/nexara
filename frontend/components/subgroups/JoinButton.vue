<!--
  @file components/subgroups/JoinButton.vue
  @brief Policy-aware join/leave button for subgroups.

  Displays different labels depending on membership state and the
  subgroup's join policy:
  - If already a member  -> "Leave" (confirm via `confirm-leave` prop handler).
  - If pending approval -> disabled "Pending" state.
  - Otherwise           -> "Join" (open) or "Request to join" (other policies).

  Emits a single `joined` or `left` event after a successful action so the
  parent can surface toast notifications.
-->
<template>
  <button
    type="button"
    :data-testid="testId"
    :disabled="loading || isPending"
    :aria-label="label"
    class="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
    :class="variantClass"
    @click="handleClick"
  >
    <span v-if="loading" data-testid="join-button-loading">
      {{ $t("common.loading") }}
    </span>
    <span v-else>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
/**
 * @brief Join/Leave button with policy-aware labels and loading state.
 */
import { computed, ref } from "vue";
import type { JoinPolicy, SubgroupRole } from "~/types/api";
import { useSubgroupsStore } from "~/stores/subgroups";
import { useUiStore } from "~/stores/ui";

const props = defineProps<{
  /** @brief Slug of the subgroup this button acts on. */
  slug: string;
  /** @brief Current viewer's membership role, or null if not a member. */
  myRole: SubgroupRole | null;
  /** @brief Join policy of the subgroup. */
  joinPolicy: JoinPolicy;
  /** @brief Whether a join request is pending approval. */
  pending?: boolean;
}>();

const emit = defineEmits<{
  joined: [];
  left: [];
  pending: [];
}>();

const { t: $t } = useI18n();
const subgroupsStore = useSubgroupsStore();
const uiStore = useUiStore();

const loading = ref(false);
const localPending = ref(false);

/** @brief Whether the current state is pending approval (prop or local). */
const isPending = computed(() => Boolean(props.pending) || localPending.value);

/** @brief Whether the viewer is already a subgroup member. */
const isMember = computed(() => props.myRole !== null);

/** @brief data-testid reflecting the current action. */
const testId = computed(() => {
  if (isMember.value) return "join-button-leave";
  if (isPending.value) return "join-button-pending";
  return "join-button-join";
});

/** @brief Human-readable label for the current state. */
const label = computed(() => {
  if (isMember.value) return $t("subgroups.leave");
  if (isPending.value) return $t("subgroups.pending");
  return props.joinPolicy === "open"
    ? $t("subgroups.join")
    : $t("subgroups.requestJoin");
});

/** @brief Tailwind classes selecting the primary / destructive variant. */
const variantClass = computed(() =>
  isMember.value
    ? "border border-border bg-background text-foreground hover:bg-destructive/10 hover:text-destructive"
    : "bg-primary text-primary-foreground hover:bg-primary/90",
);

/** @brief Handle the button click — join, leave, or pending (no-op). */
async function handleClick(): Promise<void> {
  if (loading.value || isPending.value) return;
  loading.value = true;
  try {
    if (isMember.value) {
      await subgroupsStore.leaveSubgroup(props.slug);
      uiStore.showToast({
        type: "info",
        message: $t("subgroups.leftToast"),
      });
      emit("left");
      return;
    }
    const result = await subgroupsStore.joinSubgroup(props.slug);
    if (result.status === "pending") {
      localPending.value = true;
      uiStore.showToast({
        type: "info",
        message: $t("subgroups.pendingToast"),
      });
      emit("pending");
    } else {
      uiStore.showToast({
        type: "success",
        message: $t("subgroups.joined"),
      });
      emit("joined");
    }
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : $t("common.error"),
    });
  } finally {
    loading.value = false;
  }
}
</script>
