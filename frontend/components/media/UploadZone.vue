<!--
  @file components/media/UploadZone.vue
  @brief Drag-and-drop file upload zone with progress and preview.

  Supports file picker and drag-drop. Validates file type and size
  on the client side before uploading via POST /api/v1/media/upload.
-->

<script setup lang="ts">
/**
 * @brief UploadZone component.
 * @emits upload - Emitted with the uploaded media response data.
 * @emits error - Emitted with an error message string.
 */
import { ref } from 'vue'
import { useI18n } from '#imports'
import { useAuthStore } from '~/stores/auth'

const { t } = useI18n()

const MAX_SIZE_MB = 20
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

const emit = defineEmits<{
  (e: 'upload', data: Record<string, unknown>): void
  (e: 'error', message: string): void
}>()

const dragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const previewUrl = ref<string | null>(null)
const authStore = useAuthStore()

/** @brief Validate a file before upload. */
function validate(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return `Invalid file type: ${file.type}. Allowed: JPEG, PNG, GIF, WebP.`
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB. Maximum: ${MAX_SIZE_MB}MB.`
  }
  return null
}

/** @brief Upload a single file to the media endpoint. */
async function uploadFile(file: File): Promise<void> {
  const error = validate(file)
  if (error) {
    emit('error', error)
    return
  }

  previewUrl.value = URL.createObjectURL(file)
  uploading.value = true
  progress.value = 0

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch('/api/v1/media/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${authStore.accessToken}` },
      body: formData,
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: { message: 'Upload failed' } }))
      throw new Error(err?.error?.message || `HTTP ${response.status}`)
    }

    progress.value = 100
    const data = await response.json()
    emit('upload', data)
  } catch (err) {
    emit('error', err instanceof Error ? err.message : 'Upload failed')
  } finally {
    uploading.value = false
  }
}

/** @brief Handle file input change. */
function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) uploadFile(input.files[0])
}

/** @brief Handle drag-and-drop. */
function onDrop(event: DragEvent): void {
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}
</script>

<template>
  <div
    class="relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors"
    :class="dragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <img
      v-if="previewUrl"
      :src="previewUrl"
      alt="Upload preview"
      class="mb-3 h-24 w-24 rounded object-cover"
    />

    <p class="text-sm text-muted-foreground">
      {{ uploading ? t('common.uploading', { progress }) : t('common.dragOrClick') }}
    </p>

    <input
      type="file"
      accept="image/jpeg,image/png,image/gif,image/webp"
      class="absolute inset-0 cursor-pointer opacity-0"
      :disabled="uploading"
      :aria-label="$t('common.upload')"
      @change="onFileSelect"
    />

    <div
      v-if="uploading"
      class="mt-2 h-1.5 w-full rounded-full bg-muted"
    >
      <div
        class="h-full rounded-full bg-primary transition-all"
        :style="{ width: `${progress}%` }"
      />
    </div>
  </div>
</template>
