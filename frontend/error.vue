<!--
  @file error.vue
  @brief Global Nuxt error page for 404 and server errors.

  Renders a user-friendly error page with appropriate messaging
  based on the HTTP status code. Authenticated users seeing a 404
  are offered a link back to the feed.
-->
<template>
  <div
    class="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center"
  >
    <p class="mb-2 text-6xl font-bold text-primary" data-testid="error-code">
      {{ error?.statusCode || 500 }}
    </p>
    <h1
      class="mb-4 text-2xl font-semibold text-foreground"
      data-testid="error-title"
    >
      {{ title }}
    </h1>
    <p class="mb-8 max-w-md text-muted-foreground" data-testid="error-message">
      {{ message }}
    </p>
    <div class="flex gap-4">
      <button
        class="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        @click="handleError"
      >
        {{ $t("common.goHome") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Error page logic with status-specific messaging.
 */
import { computed } from "vue";
interface NuxtError {
  statusCode?: number;
  statusMessage?: string;
  message?: string;
}

const props = defineProps<{
  /** @brief The Nuxt error object. */
  error: NuxtError | null;
}>();

/** @brief Error title based on status code. */
const title = computed(() => {
  if (props.error?.statusCode === 404) return "Page not found";
  if (props.error?.statusCode === 403) return "Access denied";
  return "Something went wrong";
});

/** @brief Error description based on status code. */
const message = computed(() => {
  if (props.error?.statusCode === 404) {
    return "The page you're looking for doesn't exist or has been moved.";
  }
  if (props.error?.statusCode === 403) {
    return "You don't have permission to access this page.";
  }
  return "An unexpected error occurred. Please try again later.";
});

/** @brief Navigate back to a safe page. */
function handleError(): void {
  clearError({ redirect: "/app" });
}
</script>
