<!--
  @file components/feed/PollCard.vue
  @brief Renders a poll in the feed with options, vote button, and results.

  Three display states:
  1. Voting: user hasn't voted, poll is open — shows selectable options + vote button
  2. Results hidden: user voted but results aren't visible yet (after_expiry) — shows confirmation
  3. Results: results are visible — shows progress bars with percentages
-->
<template>
  <div
    class="rounded-lg border border-border bg-card p-4"
    data-testid="poll-card"
  >
    <div class="mb-2 flex items-center gap-2">
      <h3 class="font-semibold text-foreground">{{ poll.question }}</h3>
      <span
        v-if="poll.is_anonymous"
        class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
      >
        {{ $t("feed.poll.anonymous") }}
      </span>
    </div>

    <!-- State 1: Voting (user hasn't voted, poll is open) -->
    <div
      v-if="state === 'voting'"
      class="space-y-2"
    >
      <label
        v-for="opt in poll.options"
        :key="opt.id"
        class="flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors"
        :class="isSelected(opt.id) ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'"
      >
        <input
          v-if="isSingleChoice"
          v-model="selectedSingle"
          type="radio"
          :value="opt.id"
          :name="`poll-${poll.id}`"
          class="h-4 w-4 text-primary"
        />
        <input
          v-else
          v-model="selectedMultiple"
          type="checkbox"
          :value="opt.id"
          class="h-4 w-4 rounded text-primary"
        />
        <span class="text-foreground">{{ opt.label }}</span>
      </label>

      <button
        type="button"
        :disabled="!hasSelection || voting"
        class="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="poll-vote-btn"
        @click="submitVote"
      >
        {{ voting ? $t("common.loading") : $t("feed.poll.vote") }}
      </button>
    </div>

    <!-- State 2: Voted but results hidden (after_expiry while poll still open) -->
    <div
      v-else-if="state === 'voted-hidden'"
      data-testid="poll-voted-hidden"
      class="space-y-2"
    >
      <div
        v-for="opt in poll.options"
        :key="opt.id"
        class="flex items-center gap-3 rounded-lg border p-3"
        :class="isUserVote(opt.id) ? 'border-primary bg-primary/5' : 'border-border'"
      >
        <span
          v-if="isUserVote(opt.id)"
          class="flex h-4 w-4 items-center justify-center text-primary"
        >&#10003;</span>
        <span v-else class="h-4 w-4" />
        <span class="text-foreground">{{ opt.label }}</span>
      </div>
      <p class="text-sm text-muted-foreground">
        {{ $t("feed.poll.voteRecorded") }}
      </p>
    </div>

    <!-- State 3: Results visible -->
    <div
      v-else
      data-testid="poll-results"
      class="space-y-3"
    >
      <div
        v-for="opt in poll.options"
        :key="opt.id"
        class="space-y-1"
      >
        <div class="flex justify-between text-sm">
          <span
            class="text-foreground"
            :class="{ 'font-medium': isUserVote(opt.id) }"
          >
            {{ opt.label }}
            <span v-if="isUserVote(opt.id)" class="text-primary">&#10003;</span>
          </span>
          <span class="text-muted-foreground">
            {{ votePercent(opt) }}%
          </span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-muted">
          <div
            class="h-full rounded-full transition-all"
            :class="isUserVote(opt.id) ? 'bg-primary' : 'bg-primary/60'"
            :style="{ width: `${votePercent(opt)}%` }"
          />
        </div>
        <!-- Voter badges (non-anonymous only) -->
        <div
          v-if="opt.voters && opt.voters.length > 0"
          class="flex flex-wrap gap-1 pt-0.5"
          data-testid="poll-voters"
        >
          <span
            v-for="voter in opt.voters"
            :key="voter.id"
            class="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
          >
            <span
              v-if="voter.avatar_url"
              class="h-3.5 w-3.5 overflow-hidden rounded-full"
            >
              <img
                :src="voter.avatar_url"
                :alt="voter.display_name"
                class="h-full w-full object-cover"
              />
            </span>
            <span
              v-else
              class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-primary text-[8px] font-bold text-primary-foreground"
            >
              {{ voter.display_name.charAt(0).toUpperCase() }}
            </span>
            {{ voter.display_name }}
          </span>
        </div>
      </div>
    </div>

    <!-- Footer: vote count + expiry -->
    <div class="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
      <span v-if="state === 'results'" data-testid="poll-vote-count">
        {{ $t("feed.poll.totalVotes", { count: poll.total_votes }) }}
      </span>
      <span v-if="poll.closed" data-testid="poll-closed">
        {{ $t("feed.poll.closed") }}
      </span>
      <span v-else-if="poll.expires_at" data-testid="poll-expiry">
        {{ expiryText }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief PollCard — displays poll and handles voting.
 */
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import type { PollResponse } from "~/types/api";

const { t } = useI18n();

const props = defineProps<{
  /** @brief The poll data to display. */
  poll: PollResponse;
}>();

const emit = defineEmits<{
  /** @brief Emitted when user submits a vote. */
  voted: [pollId: string, optionIds: string[]];
}>();

const selectedSingle = ref<string>("");
const selectedMultiple = ref<string[]>([]);
const voting = ref(false);
/** @brief Tracks local vote when results aren't returned by server (after_expiry). */
const localVoteIds = ref<string[] | null>(null);

/** @brief Whether this poll uses single-choice selection. */
const isSingleChoice = computed(
  () => props.poll.poll_type === "single" || props.poll.poll_type === "yes_no",
);

/** @brief Whether the user has selected at least one option. */
const hasSelection = computed(() =>
  isSingleChoice.value
    ? selectedSingle.value !== ""
    : selectedMultiple.value.length > 0,
);

/** @brief The user's vote IDs (from server or local optimistic). */
const effectiveUserVote = computed(
  () => props.poll.user_vote ?? localVoteIds.value,
);

/** @brief Whether the poll has ended (expired or closed). */
const pollEnded = computed(() => {
  if (props.poll.closed) return true;
  if (props.poll.expires_at && new Date(props.poll.expires_at) < new Date()) return true;
  return false;
});

/**
 * @brief Display state: 'voting' | 'voted-hidden' | 'results'
 *
 * - voting: user can vote (hasn't voted, poll open)
 * - voted-hidden: user voted but results are hidden until poll ends
 * - results: results are visible (always, after_vote+voted, after_expiry+ended)
 */
const state = computed<"voting" | "voted-hidden" | "results">(() => {
  const hasVoted = effectiveUserVote.value && effectiveUserVote.value.length > 0;

  if (props.poll.result_visibility === "always") return "results";

  if (props.poll.result_visibility === "after_expiry") {
    if (pollEnded.value) return "results";
    if (hasVoted) return "voted-hidden";
    return "voting";
  }

  // after_vote (default)
  if (hasVoted) return "results";
  if (props.poll.closed) return "results";
  return "voting";
});

/** @brief Check if an option is currently selected. */
function isSelected(optId: string): boolean {
  return isSingleChoice.value
    ? selectedSingle.value === optId
    : selectedMultiple.value.includes(optId);
}

/** @brief Check if an option was the user's vote. */
function isUserVote(optId: string): boolean {
  return effectiveUserVote.value?.includes(optId) ?? false;
}

/** @brief Human-readable expiry text. */
const expiryText = computed(() => {
  if (!props.poll.expires_at) return "";
  const expiry = new Date(props.poll.expires_at);
  const now = new Date();
  if (expiry <= now) return t("feed.poll.expired");
  const diff = expiry.getTime() - now.getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return t("feed.poll.endsIn", { time: t("feed.poll.days", { count: days }) });
  if (hours > 0) return t("feed.poll.endsIn", { time: t("feed.poll.hours", { count: hours }) });
  return t("feed.poll.endsIn", { time: t("feed.poll.minutes", { count: mins || 1 }) });
});

/** @brief Percentage of total votes for an option. */
function votePercent(opt: { vote_count: number }): number {
  if (props.poll.total_votes === 0) return 0;
  return Math.round((opt.vote_count / props.poll.total_votes) * 100);
}

/** @brief Submit selected options as vote. */
function submitVote(): void {
  if (!hasSelection.value || voting.value) return;
  voting.value = true;
  const ids = isSingleChoice.value
    ? [selectedSingle.value]
    : [...selectedMultiple.value];
  // Store locally for after_expiry polls where server won't return user_vote
  localVoteIds.value = ids;
  emit("voted", props.poll.id, ids);
}
</script>
