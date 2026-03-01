<!--
  @file pages/app/settings/security.vue
  @brief Security settings tab.

  Shows 2FA status (enabled/disabled) from auth store and
  password change form (current_password, new_password, confirm).
-->
<template>
  <div class="flex flex-1 flex-col space-y-6">
    <!-- 2FA status -->
    <div class="rounded-lg border border-border bg-card p-6">
      <h2 class="mb-2 text-lg font-medium text-foreground">
        {{ $t("settings.twoFactorStatus") }}
      </h2>
      <p class="text-muted-foreground">
        {{
          authStore.user?.totp_enabled
            ? $t("settings.twoFactorEnabled")
            : $t("settings.twoFactorDisabled")
        }}
      </p>
    </div>

    <!-- Password change form -->
    <div class="flex-1 rounded-lg border border-border bg-card p-6">
      <h2 class="mb-4 text-lg font-medium text-foreground">
        {{ $t("settings.changePassword") }}
      </h2>
      <form class="space-y-4" @submit.prevent="handlePasswordChange">
        <div>
          <label
            for="current_password"
            class="mb-1 block text-sm font-medium text-foreground"
          >
            {{ $t("settings.currentPassword") }}
          </label>
          <input
            id="current_password"
            v-model="passwordForm.current_password"
            type="password"
            required
            autocomplete="current-password"
            class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
          />
        </div>

        <div>
          <label
            for="new_password"
            class="mb-1 block text-sm font-medium text-foreground"
          >
            {{ $t("settings.newPassword") }}
          </label>
          <input
            id="new_password"
            v-model="passwordForm.new_password"
            type="password"
            required
            autocomplete="new-password"
            class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
          />
        </div>

        <div>
          <label
            for="confirm_password"
            class="mb-1 block text-sm font-medium text-foreground"
          >
            {{ $t("settings.confirmPassword") }}
          </label>
          <input
            id="confirm_password"
            v-model="passwordForm.confirm_password"
            type="password"
            required
            autocomplete="new-password"
            class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
          />
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {{ loading ? $t("common.loading") : $t("settings.changePassword") }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Security settings with 2FA status and password change.
 */
import { ref } from "vue";
import { useAuthStore } from "~/stores/auth";
import { useUiStore } from "~/stores/ui";
import { useApi } from "~/composables/useApi";

const authStore = useAuthStore();
const uiStore = useUiStore();
const api = useApi();
const { t: $t } = useI18n();

const loading = ref(false);
const passwordForm = ref({
  current_password: "",
  new_password: "",
  confirm_password: "",
});

async function handlePasswordChange(): Promise<void> {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    uiStore.showToast({
      type: "error",
      message: $t("settings.passwordMismatch"),
    });
    return;
  }

  loading.value = true;
  try {
    await api.post("/users/me/password", {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password,
    });
    uiStore.showToast({
      type: "success",
      message: $t("settings.passwordUpdated"),
    });
    passwordForm.value = {
      current_password: "",
      new_password: "",
      confirm_password: "",
    };
  } catch (error) {
    uiStore.showToast({
      type: "error",
      message: error instanceof Error ? error.message : $t("common.error"),
    });
  } finally {
    loading.value = false;
  }
}
</script>
