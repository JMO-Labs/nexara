<!--
  @file pages/auth/register.vue
  @brief Registration page with optional invite token.

  Provides a registration form with email, username, display name,
  password, and optional invite token fields. On success, redirects
  to the login page.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md">
        <h1 class="mb-6 text-center text-2xl font-bold text-foreground">
          {{ $t("auth.register") }}
        </h1>

        <div
          v-if="errorMessage"
          class="mb-4 rounded-lg bg-destructive/10 p-4 text-sm text-destructive"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <div
          v-if="success"
          class="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
          role="status"
        >
          {{ $t("auth.register") }} — redirecting to login...
        </div>

        <form class="space-y-4" @submit.prevent="handleRegister">
          <div>
            <label
              for="reg-email"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.email") }}
            </label>
            <input
              id="reg-email"
              v-model="form.email"
              type="email"
              required
              autocomplete="email"
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label
              for="reg-username"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.username") }}
            </label>
            <input
              id="reg-username"
              v-model="form.username"
              type="text"
              required
              autocomplete="username"
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label
              for="reg-display-name"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.displayName") }}
            </label>
            <input
              id="reg-display-name"
              v-model="form.display_name"
              type="text"
              required
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label
              for="reg-password"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.password") }}
            </label>
            <input
              id="reg-password"
              v-model="form.password"
              type="password"
              required
              minlength="12"
              autocomplete="new-password"
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
            />
            <p class="mt-1 text-xs text-muted-foreground">
              {{ $t("auth.passwordHint") }}
            </p>
          </div>

          <div v-if="inviteToken">
            <label
              for="reg-invite"
              class="mb-1 block text-sm font-medium text-foreground"
            >
              {{ $t("auth.inviteToken") }}
            </label>
            <input
              id="reg-invite"
              :value="inviteToken"
              type="text"
              readonly
              class="w-full rounded-lg border border-input bg-muted px-3 py-2 text-muted-foreground"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:ring-2 focus:ring-ring disabled:opacity-50"
          >
            {{ loading ? $t("common.loading") : $t("auth.register") }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-muted-foreground">
          {{ $t("auth.haveAccount") }}
          <a href="/auth/login" class="text-primary hover:underline">
            {{ $t("auth.login") }}
          </a>
        </p>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief Registration page with form handling via auth store.
 */
import { ref, reactive } from "vue";
import { useAuthStore } from "~/stores/auth";

const { t: $t } = useI18n();

definePageMeta({ layout: false });

const authStore = useAuthStore();
const route = useRoute();
const inviteToken = (route.query.invite as string) || null;

const form = reactive({
  email: "",
  username: "",
  display_name: "",
  password: "",
});

const loading = ref(false);
const errorMessage = ref("");
const success = ref(false);

async function handleRegister(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";

  if (form.password.length < 12) {
    errorMessage.value = $t("auth.errors.weakPassword");
    loading.value = false;
    return;
  }
  if (form.username.length < 3) {
    errorMessage.value = $t("auth.errors.usernameShort");
    loading.value = false;
    return;
  }

  try {
    await authStore.register({
      ...form,
      ...(inviteToken ? { invite_token: inviteToken } : {}),
    });

    success.value = true;
    setTimeout(() => {
      navigateTo("/app", { replace: true });
    }, 1500);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}
</script>
