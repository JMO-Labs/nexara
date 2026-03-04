<!--
  @file pages/auth/login.vue
  @brief Login page with local credentials and multi-provider OAuth.

  Provides an email/password form, OAuth provider buttons (from
  oauth_providers config), and links to registration and password reset.
  On successful login, redirects to the original requested page or /app.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md">
        <h1 class="mb-6 text-center text-2xl font-bold text-foreground">
          {{ $t("auth.login") }}
        </h1>

        <!-- Error message -->
        <div
          v-if="errorMessage"
          class="mb-4 rounded-lg bg-destructive/10 p-4 text-sm text-destructive"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <!-- Login form -->
        <form class="space-y-4" @submit.prevent="handleLogin">
          <div>
            <label
              for="email"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.email") }}
            </label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label
              for="password"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.password") }}
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:ring-2 focus:ring-ring disabled:opacity-50"
          >
            {{ loading ? $t("common.loading") : $t("auth.login") }}
          </button>
        </form>

        <!-- OAuth providers -->
        <div v-if="authConfig?.oauth_providers?.length" class="mt-4 space-y-2">
          <div class="relative my-4">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-border" />
            </div>
            <div class="relative flex justify-center text-xs uppercase">
              <span class="bg-background px-2 text-muted-foreground">
                {{ $t("auth.orContinueWith") }}
              </span>
            </div>
          </div>
          <button
            v-for="provider in authConfig.oauth_providers"
            :key="provider.slug"
            class="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent focus:ring-2 focus:ring-ring"
            @click="handleOAuthLogin(provider.slug)"
          >
            <img
              v-if="provider.icon_url"
              :src="provider.icon_url"
              :alt="provider.display_name"
              class="h-5 w-5"
            />
            {{ $t("auth.loginWith", { provider: provider.display_name }) }}
          </button>
        </div>

        <!-- Links -->
        <div class="mt-6 space-y-2 text-center text-sm text-muted-foreground">
          <p>
            <a href="/auth/reset-password" class="text-primary hover:underline">
              {{ $t("auth.forgotPassword") }}
            </a>
          </p>
          <p>
            {{ $t("auth.noAccount") }}
            <a href="/auth/register" class="text-primary hover:underline">
              {{ $t("auth.register") }}
            </a>
          </p>
        </div>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief Login page logic with auth store integration.
 */
import { ref } from "vue";
import { useAuthStore } from "~/stores/auth";
import type { OAuthProviderInfo } from "~/types/api";

definePageMeta({ layout: false });

const authStore = useAuthStore();
const route = useRoute();
const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref("");

/** @brief Public auth config from GET /api/v1/auth/config. */
const authConfig = ref<{
  oidc_enabled: boolean;
  registration_enabled: boolean;
  local_auth_enabled: boolean;
  oauth_providers: OAuthProviderInfo[];
} | null>(null);

onMounted(async () => {
  try {
    const res = await fetch("/api/v1/auth/config");
    if (res.ok) authConfig.value = await res.json();
  } catch {
    authConfig.value = null;
  }
});

async function handleLogin(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";

  try {
    await authStore.login({ email: email.value, password: password.value });

    if (authStore.requiresTwoFactor) {
      await navigateTo("/auth/two-factor");
      return;
    }

    const redirect = (route.query.redirect as string) || "/app";
    await navigateTo(redirect, { replace: true });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}

/** @brief Redirect to OAuth provider login. */
function handleOAuthLogin(slug: string): void {
  window.location.href = `/api/v1/oauth/${slug}/login`;
}
</script>
