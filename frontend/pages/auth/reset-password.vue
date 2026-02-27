<!--
  @file pages/auth/reset-password.vue
  @brief Password reset flow (request + confirmation).

  Two states: (1) Enter email to request a reset link, (2) Enter
  new password with a token from the URL. State is determined by
  the presence of a `token` query parameter.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md">
        <!-- Step 1: Request reset -->
        <template v-if="!resetToken">
          <h1 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
            {{ $t('auth.resetPassword') }}
          </h1>

          <div
            v-if="requestSent"
            class="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
            role="status"
          >
            {{ $t('auth.resetSent') }}
          </div>

          <form class="space-y-4" @submit.prevent="handleRequestReset">
            <div>
              <label for="reset-email" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                {{ $t('auth.email') }}
              </label>
              <input
                id="reset-email"
                v-model="email"
                type="email"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <button
              type="submit"
              :disabled="loading"
              class="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {{ $t('auth.sendResetLink') }}
            </button>
          </form>
        </template>

        <!-- Step 2: Set new password -->
        <template v-else>
          <h1 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
            {{ $t('auth.setNewPassword') }}
          </h1>

          <div
            v-if="errorMessage"
            class="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/50 dark:text-red-300"
            role="alert"
          >
            {{ errorMessage }}
          </div>

          <div
            v-if="passwordUpdated"
            class="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
            role="status"
          >
            {{ $t('auth.passwordUpdated') }}
          </div>

          <form v-if="!passwordUpdated" class="space-y-4" @submit.prevent="handleResetConfirm">
            <div>
              <label for="new-password" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                {{ $t('auth.newPassword') }}
              </label>
              <input
                id="new-password"
                v-model="newPassword"
                type="password"
                required
                minlength="12"
                autocomplete="new-password"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <button
              type="submit"
              :disabled="loading"
              class="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {{ $t('auth.setNewPassword') }}
            </button>
          </form>
        </template>

        <p class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          <a href="/auth/login" class="text-primary-600 hover:underline dark:text-primary-400">
            {{ $t('auth.login') }}
          </a>
        </p>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
/**
 * @brief Password reset page with two-step flow.
 */
import { ref } from 'vue'

definePageMeta({ layout: false })

const resetToken = typeof window !== 'undefined'
  ? new URLSearchParams(window.location.search).get('token')
  : null

const email = ref('')
const newPassword = ref('')
const loading = ref(false)
const errorMessage = ref('')
const requestSent = ref(false)
const passwordUpdated = ref(false)

async function handleRequestReset(): Promise<void> {
  loading.value = true
  try {
    await fetch('/api/v1/auth/password-reset/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: email.value }),
    })
    requestSent.value = true
  } finally {
    loading.value = false
  }
}

async function handleResetConfirm(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetch('/api/v1/auth/password-reset/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ token: resetToken, new_password: newPassword.value }),
    })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data?.error?.message || 'Reset failed')
    }
    passwordUpdated.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}
</script>
