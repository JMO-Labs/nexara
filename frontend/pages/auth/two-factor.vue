<!--
  @file pages/auth/two-factor.vue
  @brief Two-factor authentication verification page.

  Displayed after a successful password login when 2FA is required.
  Accepts a 6-digit TOTP code or a backup code to complete authentication.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md">
        <h1 class="mb-2 text-center text-2xl font-bold text-gray-900 dark:text-white">
          {{ $t('auth.twoFactor.title') }}
        </h1>
        <p class="mb-6 text-center text-sm text-gray-600 dark:text-gray-300">
          {{ $t('auth.twoFactor.enterCode') }}
        </p>

        <div
          v-if="errorMessage"
          class="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/50 dark:text-red-300"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <!-- TOTP Code form -->
        <form v-if="!showBackupInput" class="space-y-4" @submit.prevent="handleVerify">
          <div>
            <label for="totp-code" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.twoFactor.code') }}
            </label>
            <input
              id="totp-code"
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              required
              autocomplete="one-time-code"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-center text-lg tracking-widest focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              :placeholder="'000000'"
            >
          </div>

          <button
            type="submit"
            :disabled="loading || totpCode.length !== 6"
            class="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {{ $t('auth.twoFactor.verify') }}
          </button>
        </form>

        <!-- Backup code form -->
        <form v-else class="space-y-4" @submit.prevent="handleBackupVerify">
          <div>
            <label for="backup-code" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.twoFactor.backupCode') }}
            </label>
            <input
              id="backup-code"
              v-model="backupCode"
              type="text"
              required
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
          </div>

          <button
            type="submit"
            :disabled="loading || !backupCode.trim()"
            class="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {{ $t('auth.twoFactor.verify') }}
          </button>
        </form>

        <button
          class="mt-4 w-full text-center text-sm text-primary-600 hover:underline dark:text-primary-400"
          @click="showBackupInput = !showBackupInput"
        >
          {{ showBackupInput ? $t('auth.twoFactor.code') : $t('auth.twoFactor.useBackupCode') }}
        </button>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief Two-factor verification page logic using auth store.
 */
import { ref } from 'vue'
import { useAuthStore } from '~/stores/auth'

definePageMeta({ layout: false })

const authStore = useAuthStore()
const totpCode = ref('')
const backupCode = ref('')
const showBackupInput = ref(false)
const loading = ref(false)
const errorMessage = ref('')

async function handleVerify(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    await authStore.verify2fa(totpCode.value)
    await navigateTo('/app', { replace: true })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function handleBackupVerify(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    await authStore.verify2fa(backupCode.value, true)
    await navigateTo('/app', { replace: true })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}
</script>
