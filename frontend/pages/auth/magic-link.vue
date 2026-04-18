<!--
  @file pages/auth/magic-link.vue
  @brief Email input form for requesting magic link.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md">
        <h1 class="mb-6 text-center text-2xl font-bold text-foreground">
          {{ $t("magic-link.title") }}
        </h1>

        <div
          v-if="success"
          class="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
          role="status"
        >
          {{ $t("magic-link.success") }}
        </div>

        <form v-else class="space-y-4" @submit.prevent="handleSubmit">
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
              type="text"
              inputmode="email"
              required
              autocomplete="email"
              class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
              :class="{ 'border-destructive': emailError }"
              @blur="touchEmail"
            >
            <p v-if="emailError" class="mt-1 text-xs text-destructive">
              {{ emailError }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:ring-2 focus:ring-ring disabled:opacity-50"
          >
            {{ loading ? $t("common.loading") : $t("magic-link.send") }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-muted-foreground">
          <a href="/auth/login" class="text-primary hover:underline">
            {{ $t("magic-link.backToLogin") }}
          </a>
        </p>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief Magic link request form.
 */
import { ref, computed } from "vue";
import { useApi } from "~/composables/useApi";
import { validateEmail } from "~/utils/email";

definePageMeta({ layout: false });

const { t: $t } = useI18n();
const api = useApi();
const email = ref("");
const loading = ref(false);
const success = ref(false);
const emailTouched = ref(false);

const emailError = computed(() => {
  if (!emailTouched.value) return "";
  const key = validateEmail(email.value);
  return key ? $t(key) : "";
});

function touchEmail(): void {
  emailTouched.value = true;
}

async function handleSubmit(): Promise<void> {
  emailTouched.value = true;
  const emailKey = validateEmail(email.value);
  if (emailKey) return;

  loading.value = true;
  try {
    await api.post("/auth/magic-link/request", { email: email.value });
    success.value = true;
  } catch {
    success.value = true;
  } finally {
    loading.value = false;
  }
}
</script>
