<!--
  @file components/feed/PostComposer.vue
  @brief New post creation form with Markdown input and media attachment.

  Handles post creation end-to-end: text input, media upload/attachment,
  API submission via the feed store, and form reset on success.
  Includes discard button and removable media thumbnail strip.
-->
<template>
  <form
    class="rounded-lg border border-border bg-card p-4 shadow-sm"
    @submit.prevent="handleSubmit"
  >
    <textarea
      v-model="content"
      :placeholder="$t('feed.createPost')"
      :aria-label="$t('feed.createPost')"
      class="w-full resize-none rounded-md border-0 bg-muted p-3 text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
      rows="3"
    />

    <!-- Attached media thumbnail strip -->
    <div v-if="mediaItems.length > 0" class="mt-2 flex flex-wrap gap-2">
      <div
        v-for="item in mediaItems"
        :key="item.id"
        class="group relative h-16 w-16 overflow-hidden rounded-md border border-border"
      >
        <img
          v-if="item.thumbnailUrl"
          :src="item.thumbnailUrl"
          alt=""
          class="h-full w-full object-cover"
        >
        <div
          v-else
          class="flex h-full w-full items-center justify-center bg-muted text-xs text-muted-foreground"
        >
          IMG
        </div>
        <button
          type="button"
          class="absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100"
          :aria-label="$t('feed.removeMedia')"
          @click="removeMedia(item.id)"
        >
          &times;
        </button>
      </div>
    </div>

    <div v-if="showUpload" class="mt-2">
      <UploadZone
        :key="uploadKey"
        @upload="onUploadComplete"
        @error="onUploadError"
      />
    </div>
    <div class="mt-2 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="relative inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          :aria-label="$t('feed.attachMedia')"
          @click="showUpload = !showUpload"
        >
          {{ $t("feed.attachMedia") }}
          <span
            v-if="mediaItems.length > 0"
            class="inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground"
            :aria-label="
              $t('feed.mediaAttachedCount', { count: mediaItems.length })
            "
          >
            {{ mediaItems.length }}
          </span>
        </button>
        <button
          v-if="isDirty"
          type="button"
          class="text-sm text-destructive transition-colors hover:text-destructive/80"
          @click="handleDiscard"
        >
          {{ $t("feed.discard") }}
        </button>
      </div>
      <button
        type="submit"
        :disabled="submitting || (!content.trim() && mediaItems.length === 0)"
        class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      >
        {{ submitting ? $t("common.loading") : $t("feed.submit") }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
/**
 * @brief PostComposer component — owns form state and submission lifecycle.
 */
import { ref, computed } from "vue";
import UploadZone from "~/components/media/UploadZone.vue";
import { useFeedStore } from "~/stores/feed";
import { useUiStore } from "~/stores/ui";
import { useAuthStore } from "~/stores/auth";

/** @brief Tracks an uploaded media item with preview info. */
interface MediaItem {
  id: string;
  thumbnailUrl: string | null;
}

const feedStore = useFeedStore();
const uiStore = useUiStore();
const authStore = useAuthStore();

const content = ref("");
/** @brief Uploaded media items with IDs and thumbnail URLs. */
const mediaItems = ref<MediaItem[]>([]);
/** @brief Whether the UploadZone is visible. */
const showUpload = ref(false);
/** @brief Whether a submission is in flight. */
const submitting = ref(false);
/** @brief Key used to force-remount UploadZone and clear its preview. */
const uploadKey = ref(0);

/** @brief True when the composer has unsaved content or media. */
const isDirty = computed(
  () => content.value.trim().length > 0 || mediaItems.value.length > 0,
);

const emit = defineEmits<{
  /** @brief Emitted after a post is successfully created. */
  (e: "created"): void;
}>();

/** @brief Handle UploadZone upload event; add media item to the collection. */
function onUploadComplete(data: Record<string, unknown>): void {
  const id = data?.id;
  if (id != null && typeof id === "string") {
    const thumbnailUrl =
      (data?.thumbnail_url as string) ??
      (data?._localPreviewUrl as string) ??
      null;
    mediaItems.value = [...mediaItems.value, { id, thumbnailUrl }];
  }
}

/** @brief Handle UploadZone error event; show toast to user. */
function onUploadError(message: string): void {
  uiStore.showToast({ type: "error", message });
}

/**
 * @brief Remove an attached media item and delete it from the server.
 * @param mediaId The media UUID to remove.
 */
async function removeMedia(mediaId: string): Promise<void> {
  const removed = mediaItems.value.find((m) => m.id === mediaId);
  if (removed?.thumbnailUrl?.startsWith("blob:")) {
    URL.revokeObjectURL(removed.thumbnailUrl);
  }
  mediaItems.value = mediaItems.value.filter((m) => m.id !== mediaId);
  try {
    await fetch(`/api/v1/media/${mediaId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${authStore.accessToken}` },
    });
  } catch {
    /* Best-effort cleanup; orphaned media is acceptable */
  }
}

/** @brief Discard all composer content and attached media. */
async function handleDiscard(): Promise<void> {
  const items = [...mediaItems.value];
  const ids = items.map((m) => m.id);
  for (const m of items) {
    if (m.thumbnailUrl?.startsWith("blob:"))
      URL.revokeObjectURL(m.thumbnailUrl);
  }
  content.value = "";
  mediaItems.value = [];
  showUpload.value = false;
  uploadKey.value++;

  for (const id of ids) {
    try {
      await fetch(`/api/v1/media/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${authStore.accessToken}` },
      });
    } catch {
      /* Best-effort cleanup */
    }
  }
}

/**
 * @brief Submit the post via feed store; clear form only on success.
 *
 * Allows image-only posts (no text required when media is attached).
 * On failure, preserves the form so the user can retry.
 */
async function handleSubmit(): Promise<void> {
  const hasContent = content.value.trim().length > 0;
  const hasMedia = mediaItems.value.length > 0;
  if (!hasContent && !hasMedia) return;

  submitting.value = true;
  try {
    const postContent = hasContent ? content.value : "";
    await feedStore.createPost(
      postContent,
      mediaItems.value.map((m) => m.id),
    );
    for (const m of mediaItems.value) {
      if (m.thumbnailUrl?.startsWith("blob:"))
        URL.revokeObjectURL(m.thumbnailUrl);
    }
    content.value = "";
    mediaItems.value = [];
    showUpload.value = false;
    uploadKey.value++;
    emit("created");
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : "Failed to create post",
    });
  } finally {
    submitting.value = false;
  }
}
</script>
