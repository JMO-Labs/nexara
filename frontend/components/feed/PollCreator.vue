<!--
  @file components/feed/PollCreator.vue
  @brief Form for creating polls with question, type, options, expiry, visibility.

  Supports single, multiple, yes_no, photo poll types.
  Yes/No auto-fills options. Min 2, max 10 options.
  Expiry uses quick-select duration presets with optional custom datetime.
  Emits create(data: PollCreate) on submit.
-->
<template>
  <form
    class="space-y-4 rounded-lg border border-border bg-card p-4"
    @submit.prevent="handleSubmit"
  >
    <div>
      <label
        for="poll-question"
        class="mb-1 block text-sm font-medium text-foreground"
      >
        {{ $t("feed.poll.question") }}
      </label>
      <input
        id="poll-question"
        v-model="question"
        type="text"
        class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
        :placeholder="$t('feed.poll.question')"
        data-testid="poll-question"
      />
    </div>

    <div>
      <label class="mb-1 block text-sm font-medium text-foreground">
        {{ $t("feed.poll.pollType") }}
      </label>
      <select
        v-model="pollType"
        class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
        data-testid="poll-type"
        @change="onPollTypeChange"
      >
        <option value="single">{{ $t("feed.poll.single") }}</option>
        <option value="multiple">{{ $t("feed.poll.multiple") }}</option>
        <option value="yes_no">{{ $t("feed.poll.yesNo") }}</option>
        <option value="photo">{{ $t("feed.poll.photo") }}</option>
      </select>
    </div>

    <div>
      <label class="mb-1 block text-sm font-medium text-foreground">
        {{ $t("feed.poll.addOption") }}
      </label>
      <div class="space-y-2">
        <div
          v-for="(opt, idx) in options"
          :key="idx"
          class="flex gap-2"
        >
          <input
            v-model="opt.label"
            type="text"
            class="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-foreground"
            :data-testid="`poll-option-${idx}`"
          />
          <button
            v-if="options.length > 2"
            type="button"
            class="rounded-lg border border-border px-3 py-2 text-muted-foreground hover:bg-muted"
            :aria-label="$t('common.delete')"
            @click="removeOption(idx)"
          >
            &times;
          </button>
        </div>
        <button
          v-if="options.length < 10"
          type="button"
          class="rounded-lg border border-dashed border-border px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
          data-testid="add-option"
          @click="addOption"
        >
          {{ $t("feed.poll.addOption") }}
        </button>
      </div>
    </div>

    <div>
      <label class="mb-1 block text-sm font-medium text-foreground">
        {{ $t("feed.poll.duration") }}
      </label>
      <div class="flex flex-wrap gap-2" data-testid="duration-presets">
        <button
          v-for="preset in durationPresets"
          :key="preset.value"
          type="button"
          class="rounded-full border px-3 py-1 text-sm transition-colors"
          :class="selectedDuration === preset.value
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-border text-muted-foreground hover:bg-muted'"
          :data-testid="`duration-${preset.value}`"
          @click="selectDuration(preset.value)"
        >
          {{ preset.label }}
        </button>
      </div>
      <!-- Custom datetime fallback -->
      <div v-if="selectedDuration === 'custom'" class="mt-2">
        <input
          id="poll-expires"
          v-model="customExpiresAt"
          type="datetime-local"
          :min="minDatetime"
          class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
          data-testid="poll-expires"
        />
      </div>
    </div>

    <div class="flex items-center gap-4">
      <label class="flex cursor-pointer items-center gap-2">
        <input
          v-model="isAnonymous"
          type="checkbox"
          class="h-4 w-4 rounded text-primary"
        />
        <span class="text-sm text-foreground">{{ $t("feed.poll.anonymous") }}</span>
      </label>
    </div>

    <div>
      <label class="mb-1 block text-sm font-medium text-foreground">
        {{ $t("feed.poll.resultVisibility") }}
      </label>
      <select
        v-model="resultVisibility"
        class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground"
        data-testid="result-visibility"
      >
        <option value="after_vote">{{ $t("feed.poll.afterVote") }}</option>
        <option value="always">{{ $t("feed.poll.always") }}</option>
        <option value="after_expiry">{{ $t("feed.poll.afterExpiry") }}</option>
      </select>
    </div>

    <button
      type="submit"
      :disabled="!canSubmit"
      class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {{ $t("feed.poll.createPoll") }}
    </button>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief PollCreator — form for creating polls.
 */
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import type { PollCreate, PollOptionCreate } from "~/types/api";

const { t } = useI18n();
const emit = defineEmits<{
  /** @brief Emitted with poll data on submit. */
  create: [data: PollCreate];
}>();

const question = ref("");
const pollType = ref<PollCreate["poll_type"]>("single");
const options = ref<{ label: string }[]>([{ label: "" }, { label: "" }]);
const selectedDuration = ref<string>("1d");
const customExpiresAt = ref("");
const isAnonymous = ref(false);
const resultVisibility = ref<PollCreate["result_visibility"]>("after_vote");

/** @brief Duration presets for poll expiry. */
const durationPresets = computed(() => [
  { value: "1h", label: t("feed.poll.duration1h") },
  { value: "6h", label: t("feed.poll.duration6h") },
  { value: "1d", label: t("feed.poll.duration1d") },
  { value: "3d", label: t("feed.poll.duration3d") },
  { value: "7d", label: t("feed.poll.duration7d") },
  { value: "none", label: t("feed.poll.noExpiry") },
  { value: "custom", label: t("feed.poll.custom") },
]);

/** @brief Minimum datetime for custom picker (now). */
const minDatetime = computed(() => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
});

/** @brief Select a duration preset. */
function selectDuration(value: string): void {
  selectedDuration.value = value;
}

/** @brief Compute ISO expiry string from selected duration. */
function computeExpiresAt(): string | null {
  if (selectedDuration.value === "none") return null;
  if (selectedDuration.value === "custom") {
    return customExpiresAt.value || null;
  }
  const now = new Date();
  const map: Record<string, number> = {
    "1h": 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
  };
  const ms = map[selectedDuration.value];
  if (!ms) return null;
  return new Date(now.getTime() + ms).toISOString();
}

/** @brief Whether form can be submitted (question + at least 2 non-empty options). */
const canSubmit = computed(() => {
  const filled = options.value.filter((o) => o.label.trim()).length;
  return question.value.trim().length > 0 && filled >= 2;
});

/** @brief When switching to yes_no, auto-fill options. */
function onPollTypeChange(): void {
  if (pollType.value === "yes_no") {
    options.value = [{ label: t("common.yes") }, { label: t("common.no") }];
  }
}

/** @brief Add a new empty option. */
function addOption(): void {
  if (options.value.length < 10) {
    options.value.push({ label: "" });
  }
}

/** @brief Remove option at index. */
function removeOption(idx: number): void {
  if (options.value.length > 2) {
    options.value.splice(idx, 1);
  }
}

/** @brief Submit poll creation. */
function handleSubmit(): void {
  if (!canSubmit.value) return;
  const opts: PollOptionCreate[] = options.value
    .filter((o) => o.label.trim())
    .map((o) => ({ label: o.label.trim() }));
  emit("create", {
    question: question.value.trim(),
    poll_type: pollType.value,
    options: opts,
    expires_at: computeExpiresAt(),
    is_anonymous: isAnonymous.value,
    result_visibility: resultVisibility.value,
  });
}
</script>
