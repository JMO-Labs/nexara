<!--
  @file components/media/UploadZone.vue
  @brief Drag-and-drop file upload zone with multi-file support.

  Supports file picker and drag-drop for multiple files. Validates file
  type and size on the client side before uploading each file via
  POST /api/v1/media/upload.
-->

<script setup lang="ts">
/**
 * @brief UploadZone component with multi-file support.
 * @emits upload - Emitted per file with the uploaded media response data.
 * @emits error - Emitted with an error message string.
 */
import { ref } from "vue";
import { useI18n } from "#imports";
import { useAuthStore } from "~/stores/auth";

const { t } = useI18n();

const MAX_SIZE_MB = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

const emit = defineEmits<{
  (e: "upload", data: Record<string, unknown>): void;
  (e: "error", message: string): void;
}>();

const dragging = ref(false);
const uploading = ref(false);
const progress = ref(0);
const authStore = useAuthStore();

/** @brief Validate a file before upload. */
function validate(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return `Invalid file type: ${file.type}. Allowed: JPEG, PNG, GIF, WebP.`;
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB. Maximum: ${MAX_SIZE_MB}MB.`;
  }
  return null;
}

/** @brief Upload a single file to the media endpoint. */
async function uploadSingleFile(file: File): Promise<void> {
  const error = validate(file);
  if (error) {
    emit("error", error);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/v1/media/upload", {
    method: "POST",
    headers: { Authorization: `Bearer ${authStore.accessToken}` },
    body: formData,
  });

  if (!response.ok) {
    const err = await response
      .json()
      .catch(() => ({ error: { message: "Upload failed" } }));
    throw new Error(err?.error?.message || `HTTP ${response.status}`);
  }

  const data = await response.json();
  data._localPreviewUrl = URL.createObjectURL(file);
  emit("upload", data);
}

/**
 * @brief Process a FileList, uploading each valid file sequentially.
 * @param files The FileList from input or drag-drop.
 */
async function processFiles(files: FileList): Promise<void> {
  if (files.length === 0) return;

  uploading.value = true;
  progress.value = 0;

  let completed = 0;
  for (const file of Array.from(files)) {
    try {
      await uploadSingleFile(file);
    } catch (err) {
      emit("error", err instanceof Error ? err.message : "Upload failed");
    }
    completed++;
    progress.value = Math.round((completed / files.length) * 100);
  }

  uploading.value = false;
}

/** @brief Handle file input change (supports multiple files). */
function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    processFiles(input.files);
  }
}

/** @brief Handle drag-and-drop (supports multiple files). */
function onDrop(event: DragEvent): void {
  dragging.value = false;
  const files = event.dataTransfer?.files;
  if (files && files.length > 0) {
    processFiles(files);
  }
}
</script>

<template>
  <div
    class="relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors"
    :class="
      dragging
        ? 'border-primary bg-primary/5'
        : 'border-border hover:border-primary/50'
    "
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <p class="text-sm text-muted-foreground">
      {{
        uploading
          ? t("common.uploading", { progress })
          : t("common.dragOrClick")
      }}
    </p>

    <input
      type="file"
      multiple
      accept="image/jpeg,image/png,image/gif,image/webp"
      class="absolute inset-0 cursor-pointer opacity-0"
      :disabled="uploading"
      :aria-label="$t('common.upload')"
      @change="onFileSelect"
    >

    <div v-if="uploading" class="mt-2 h-1.5 w-full rounded-full bg-muted">
      <div
        class="h-full rounded-full bg-primary transition-all"
        :style="{ width: `${progress}%` }"
      />
    </div>
  </div>
</template>
