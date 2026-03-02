<!--
  @file pages/auth/callback.vue
  @brief OAuth callback page that exchanges an authorization code for JWT tokens.

  The backend redirects here with ?code=... after successful OAuth authentication.
  This page exchanges the code for tokens and redirects to the app.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md text-center">
        <div v-if="error" class="space-y-4">
          <div
            class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive"
            role="alert"
          >
            {{ error }}
          </div>
          <a
            href="/auth/login"
            class="inline-block text-sm text-primary hover:underline"
          >
            {{ $t("auth.backToLogin") }}
          </a>
        </div>
        <div v-else class="space-y-4">
          <div
            class="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
          />
          <p class="text-sm text-muted-foreground">
            {{ $t("auth.completing") }}
          </p>
        </div>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief OAuth callback logic — exchanges code for tokens.
 */
import { ref, onMounted } from "vue";
import { useAuthStore } from "~/stores/auth";

definePageMeta({ layout: false });

const authStore = useAuthStore();
const route = useRoute();
const { t: $t } = useI18n();
const error = ref<string | null>(null);

onMounted(async () => {
  const code = route.query.code as string | undefined;
  const errorParam = route.query.error as string | undefined;

  if (errorParam) {
    error.value = errorParam;
    return;
  }

  if (!code) {
    error.value = $t("auth.authenticationFailed");
    return;
  }

  try {
    const response = await fetch("/api/v1/oauth/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      error.value =
        data?.error?.message || data?.detail || $t("auth.authenticationFailed");
      return;
    }

    const data = await response.json();
    authStore.accessToken = data.access_token;
    await authStore.fetchUser();
    await navigateTo("/app", { replace: true });
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : $t("auth.authenticationFailed");
  }
});
</script>
