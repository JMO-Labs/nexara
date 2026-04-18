<!--
  @file pages/auth/magic-link-verify.vue
  @brief Auto-verifies token from URL query param.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md text-center">
        <div v-if="loading" class="space-y-4">
          <div
            class="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
          />
          <p class="text-sm text-muted-foreground">
            {{ $t("magic-link.verifying") }}
          </p>
        </div>

        <div v-else-if="error" class="space-y-4">
          <div
            class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive"
            role="alert"
          >
            {{ error }}
          </div>
          <a
            href="/auth/magic-link"
            class="inline-block text-sm text-primary hover:underline"
          >
            {{ $t("magic-link.tryAgain") }}
          </a>
        </div>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief Magic link verification — exchanges token for JWT.
 */
import { ref, onMounted } from "vue";
import { useAuthStore } from "~/stores/auth";
import { useApi } from "~/composables/useApi";

definePageMeta({ layout: false });

const authStore = useAuthStore();
const route = useRoute();
const api = useApi();
const loading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  const token = route.query.token as string | undefined;

  if (!token) {
    error.value = "Invalid magic link";
    loading.value = false;
    return;
  }

  try {
    const data = await api.get<{ access_token: string }>(
      `/auth/magic-link/verify?token=${encodeURIComponent(token)}`,
    );
    if (data?.access_token) {
      authStore.accessToken = data.access_token;
      await authStore.fetchUser();
      await navigateTo("/app", { replace: true });
    } else {
      error.value = "Invalid response";
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Verification failed";
  } finally {
    loading.value = false;
  }
});
</script>
