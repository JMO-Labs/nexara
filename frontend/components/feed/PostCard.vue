<!--
  @file components/feed/PostCard.vue
  @brief Post display card with content, media, reactions, comments, and owner controls.

  Renders a single post in the activity feed. Content is Markdown-rendered
  and sanitized. The post author (or admin) sees an actions menu with
  edit and delete options. Inline editing replaces the content area with
  a textarea.
-->
<template>
  <article
    class="cursor-pointer rounded-lg border border-border bg-card p-4 shadow-sm transition-colors hover:bg-card/80"
    @click="navigateToPost"
  >
    <!-- Author header -->
    <div class="mb-3 flex items-center gap-3">
      <div
        class="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground"
        :aria-label="post.author.display_name"
      >
        {{ post.author.display_name.charAt(0).toUpperCase() }}
      </div>
      <div class="min-w-0 flex-1">
        <p class="font-semibold text-card-foreground">
          {{ post.author.display_name }}
        </p>
        <p class="text-xs text-muted-foreground">
          @{{ post.author.username }} &middot;
          <NuxtLink
            :to="`/app/post/${post.id}`"
            data-testid="post-detail-link"
            class="hover:underline"
          >
            {{ timeAgo(post.created_at) }}
          </NuxtLink>
        </p>
      </div>

      <!-- Actions menu (author or admin only) -->
      <PostActions
        v-if="canManage"
        @edit="startEditing"
        @delete="confirmDelete"
      />
    </div>

    <!-- Inline edit mode -->
    <div v-if="editing" class="mb-3">
      <textarea
        ref="editTextarea"
        v-model="editContent"
        class="w-full resize-none rounded-md border border-input bg-muted p-3 text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
        rows="4"
      />
      <div class="mt-2 flex items-center justify-end gap-2">
        <button
          class="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent"
          @click="cancelEditing"
        >
          {{ $t("common.cancel") }}
        </button>
        <button
          :disabled="saving || !editContent.trim()"
          class="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          @click="saveEdit"
        >
          {{ saving ? $t("common.loading") : $t("common.save") }}
        </button>
      </div>
    </div>

    <!-- Post content (Markdown rendered) -->
    <div
      v-else
      data-testid="post-content"
      class="prose prose-sm max-w-none dark:prose-invert mb-3"
      v-html="renderedContent"
    />

    <!-- Media grid -->
    <div v-if="post.media.length" class="mb-1">
      <MediaGrid :items="post.media" @open="openLightbox" />
    </div>

    <!-- Full-size media lightbox -->
    <MediaLightbox
      v-if="lightboxOpen"
      :items="post.media"
      :start-index="lightboxIndex"
      @close="lightboxOpen = false"
    />

    <!-- Reactions -->
    <ReactionBar
      :reactions="post.reactions"
      :post-id="post.id"
      @react="(postId: string, emoji: string) => $emit('react', postId, emoji)"
    />

    <!-- Comment toggle -->
    <button
      class="mt-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
      @click="toggleComments"
    >
      <span v-if="!commentsOpen">
        {{ post.comment_count }} {{ $t("feed.comments") }}
      </span>
      <span v-else>
        {{ $t("common.close") }}
        ({{ post.comment_count }} {{ $t("feed.comments") }})
      </span>
    </button>

    <!-- Expanding comment drawer -->
    <div v-if="commentsOpen" class="mt-3 border-t border-border pt-3">
      <LoadingSpinner v-if="loadingComments" />
      <template v-else>
        <!-- Expanded mode: scrollable container with all loaded comments -->
        <div
          v-if="expanded"
          ref="scrollContainer"
          class="max-h-96 overflow-y-auto rounded-md"
        >
          <CommentThread
            :comments="allLoadedComments"
            :post-id="post.id"
            :show-load-more="hasMorePages"
            @add-comment="handleAddComment"
            @load-more="loadMoreComments"
          />
        </div>

        <!-- Preview mode: latest 3 comments -->
        <CommentThread
          v-else
          :comments="previewComments"
          :post-id="post.id"
          @add-comment="handleAddComment"
        />

        <!-- Expand / collapse controls -->
        <div class="mt-2 flex justify-center">
          <button
            v-if="!expanded && hasMoreComments"
            class="text-sm text-muted-foreground transition-colors hover:text-foreground"
            @click="expandComments"
          >
            {{ $t("feed.showAllComments", { count: post.comment_count }) }}
          </button>
          <button
            v-else-if="expanded"
            class="text-sm text-muted-foreground transition-colors hover:text-foreground"
            @click="expanded = false"
          >
            {{ $t("feed.showLess") }}
          </button>
        </div>
      </template>
    </div>

    <!-- Delete confirmation dialog -->
    <Teleport to="body">
      <div
        v-if="showDeleteConfirm"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div
          class="fixed inset-0 bg-background/80 backdrop-blur-sm"
          @click="showDeleteConfirm = false"
        />
        <div
          class="relative z-10 w-full max-w-sm rounded-lg border border-border bg-popover p-6 shadow-lg"
          role="alertdialog"
        >
          <p class="mb-4 text-sm text-foreground">
            {{ $t("feed.deleteConfirm") }}
          </p>
          <div class="flex justify-end gap-2">
            <button
              class="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent"
              @click="showDeleteConfirm = false"
            >
              {{ $t("common.cancel") }}
            </button>
            <button
              :disabled="deleting"
              class="rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 disabled:opacity-50"
              @click="executeDelete"
            >
              {{ deleting ? $t("common.loading") : $t("common.delete") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </article>
</template>

<script setup lang="ts">
/**
 * @brief PostCard component with inline editing and delete confirmation.
 */
import { ref, computed, nextTick } from "vue";
import { useRouter } from "vue-router";
import type { Post, Comment } from "~/types/api";
import { renderMarkdown } from "~/utils/markdown";
import { timeAgo } from "~/utils/date";
import { useAuthStore } from "~/stores/auth";
import { useFeedStore } from "~/stores/feed";
import { useUiStore } from "~/stores/ui";
import ReactionBar from "~/components/feed/ReactionBar.vue";
import PostActions from "~/components/feed/PostActions.vue";
import CommentThread from "~/components/feed/CommentThread.vue";
import LoadingSpinner from "~/components/common/LoadingSpinner.vue";
import MediaGrid from "~/components/media/MediaGrid.vue";
import MediaLightbox from "~/components/media/MediaLightbox.vue";
import { buildCommentTree } from "~/utils/comments";

const props = defineProps<{
  /** @brief The post to render. */
  post: Post;
}>();

defineEmits<{
  (e: "react", postId: string, emoji: string): void;
}>();

const router = useRouter();
const authStore = useAuthStore();
const feedStore = useFeedStore();
const uiStore = useUiStore();

/** @brief Interactive element tags that should not trigger post navigation. */
const INTERACTIVE_TAGS = new Set(["A", "BUTTON", "INPUT", "TEXTAREA", "SELECT"]);

/**
 * @brief Navigate to the post detail page on card click.
 *
 * Skips navigation when the click originates from an interactive
 * element (link, button, input, etc.) or when in editing/comments mode.
 */
function navigateToPost(event: MouseEvent): void {
  let el = event.target as HTMLElement | null;
  while (el && el !== event.currentTarget) {
    if (INTERACTIVE_TAGS.has(el.tagName) || el.getAttribute("role") === "button") return;
    el = el.parentElement;
  }
  if (editing.value || commentsOpen.value) return;
  router.push(`/app/post/${props.post.id}`);
}

/** @brief Whether the current user can edit/delete this post. */
const canManage = computed(() => {
  const userId = authStore.user?.id;
  const role = authStore.user?.role;
  return userId === props.post.author.id || role === "admin";
});

/** @brief Markdown content rendered to sanitized HTML. */
const renderedContent = computed(() => renderMarkdown(props.post.content));

/** @brief Whether the media lightbox overlay is open. */
const lightboxOpen = ref(false);

/** @brief Index of the media item to show first in the lightbox. */
const lightboxIndex = ref(0);

const editing = ref(false);
const editContent = ref("");
const saving = ref(false);
const editTextarea = ref<HTMLTextAreaElement | null>(null);

const showDeleteConfirm = ref(false);
const deleting = ref(false);

const commentsOpen = ref(false);
const loadingComments = ref(false);
const expanded = ref(false);
const scrollContainer = ref<HTMLElement | null>(null);

/** @brief Maximum comments shown in preview mode. */
const COMMENT_PREVIEW_LIMIT = 3;

/** @brief Paginated comment entry for this post from the store. */
const commentEntry = computed(
  () => feedStore.commentsByPost[props.post.id],
);

/** @brief All loaded comments nested into a tree (newest first). */
const allLoadedComments = computed<Comment[]>(() =>
  buildCommentTree(commentEntry.value?.items ?? []),
);

/** @brief First N top-level comments for the collapsed preview. */
const previewComments = computed<Comment[]>(() =>
  allLoadedComments.value.slice(0, COMMENT_PREVIEW_LIMIT),
);

/** @brief Whether there are more comments than the preview shows. */
const hasMoreComments = computed(
  () => props.post.comment_count > COMMENT_PREVIEW_LIMIT,
);

/** @brief Whether more pages can be fetched from the server. */
const hasMorePages = computed(
  () => commentEntry.value?.hasMore ?? false,
);

async function toggleComments(): Promise<void> {
  commentsOpen.value = !commentsOpen.value;
  expanded.value = false;
  if (commentsOpen.value && allLoadedComments.value.length === 0) {
    loadingComments.value = true;
    try {
      await feedStore.fetchComments(props.post.id, true);
    } catch (err) {
      uiStore.showToast({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to load comments",
      });
    } finally {
      loadingComments.value = false;
    }
  }
}

/** @brief Switch from preview to expanded mode. */
function expandComments(): void {
  expanded.value = true;
}

/** @brief Fetch the next page of older comments. */
async function loadMoreComments(): Promise<void> {
  try {
    await feedStore.fetchComments(props.post.id);
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : "Failed to load comments",
    });
  }
}

async function handleAddComment(payload: {
  postId: string;
  content: string;
  parentId: string | null;
}): Promise<void> {
  try {
    await feedStore.addComment(payload.postId, payload.content, payload.parentId);
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : "Failed to add comment",
    });
  }
}

function startEditing(): void {
  editContent.value = props.post.content;
  editing.value = true;
  nextTick(() => editTextarea.value?.focus());
}

function cancelEditing(): void {
  editing.value = false;
  editContent.value = "";
}

async function saveEdit(): Promise<void> {
  if (!editContent.value.trim()) return;
  saving.value = true;
  try {
    await feedStore.editPost(props.post.id, editContent.value);
    editing.value = false;
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : "Failed to save",
    });
  } finally {
    saving.value = false;
  }
}

/** @brief Open the media lightbox at the given index. */
function openLightbox(index: number): void {
  lightboxIndex.value = index;
  lightboxOpen.value = true;
}

function confirmDelete(): void {
  showDeleteConfirm.value = true;
}

async function executeDelete(): Promise<void> {
  deleting.value = true;
  try {
    await feedStore.deletePost(props.post.id);
    showDeleteConfirm.value = false;
  } catch (err) {
    uiStore.showToast({
      type: "error",
      message: err instanceof Error ? err.message : "Failed to delete",
    });
  } finally {
    deleting.value = false;
  }
}
</script>
