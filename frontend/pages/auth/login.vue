<!--
  @file pages/auth/login.vue
  @brief Login page with local credentials and OIDC support.

  Provides an email/password form, OIDC SSO button, and links to
  registration and password reset pages. On successful login, redirects
  to the original requested page or the feed.
-->
<template>
  <NuxtLayout name="public">
    <div class="flex min-h-screen items-center justify-center px-4">
      <div class="w-full max-w-md">
        <h1 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
          {{ $t('auth.login') }}
        </h1>

        <!-- Error message -->
        <div
          v-if="errorMessage"
          class="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/50 dark:text-red-300"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <!-- Login form -->
        <form class="space-y-4" @submit.prevent="handleLogin">
          <div>
            <label for="email" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.email') }}
            </label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
          </div>

          <div>
            <label for="password" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.password') }}
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {{ loading ? $t('common.loading') : $t('auth.login') }}
          </button>
        </form>

        <!-- OIDC login -->
        <div class="mt-4">
          <button
            class="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
            @click="handleOidcLogin"
          >
            {{ $t('auth.loginWithOidc') }}
          </button>
        </div>

        <!-- Links -->
        <div class="mt-6 space-y-2 text-center text-sm text-gray-600 dark:text-gray-400">
          <p>
            <a href="/auth/reset-password" class="text-primary-600 hover:underline dark:text-primary-400">
              {{ $t('auth.forgotPassword') }}
            </a>
          </p>
          <p>
            {{ $t('auth.noAccount') }}
            <a href="/auth/register" class="text-primary-600 hover:underline dark:text-primary-400">
              {{ $t('auth.register') }}
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
import { ref } from 'vue'
import { useAuthStore } from '~/stores/auth'

definePageMeta({ layout: false })

const authStore = useAuthStore()
const route = useRoute()
const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function handleLogin(): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login({ email: email.value, password: password.value })

    if (authStore.requiresTwoFactor) {
      await navigateTo('/auth/two-factor')
      return
    }

    const redirect = (route.query.redirect as string) || '/app'
    await navigateTo(redirect, { replace: true })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function handleOidcLogin(): void {
  window.location.href = '/api/v1/auth/oidc/login'
}
</script>
