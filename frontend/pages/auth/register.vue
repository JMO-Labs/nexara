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
        <h1 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
          {{ $t('auth.register') }}
        </h1>

        <div
          v-if="errorMessage"
          class="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/50 dark:text-red-300"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <div
          v-if="success"
          class="mb-4 rounded-lg bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
          role="status"
        >
          {{ $t('auth.register') }} — redirecting to login...
        </div>

        <form class="space-y-4" @submit.prevent="handleRegister">
          <div>
            <label for="reg-email" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.email') }}
            </label>
            <input
              id="reg-email"
              v-model="form.email"
              type="email"
              required
              autocomplete="email"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label for="reg-username" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.username') }}
            </label>
            <input
              id="reg-username"
              v-model="form.username"
              type="text"
              required
              autocomplete="username"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label for="reg-display-name" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.displayName') }}
            </label>
            <input
              id="reg-display-name"
              v-model="form.display_name"
              type="text"
              required
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label for="reg-password" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.password') }}
            </label>
            <input
              id="reg-password"
              v-model="form.password"
              type="password"
              required
              minlength="12"
              autocomplete="new-password"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {{ $t('auth.passwordHint') }}
            </p>
          </div>

          <div v-if="inviteToken">
            <label for="reg-invite" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ $t('auth.inviteToken') }}
            </label>
            <input
              id="reg-invite"
              :value="inviteToken"
              type="text"
              readonly
              class="w-full rounded-lg border border-gray-200 bg-gray-100 px-3 py-2 text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {{ loading ? $t('common.loading') : $t('auth.register') }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          {{ $t('auth.haveAccount') }}
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
 * @brief Registration page with form handling via auth store.
 */
import { ref, reactive } from 'vue'
import { useAuthStore } from '~/stores/auth'

const { t: $t } = useI18n()

definePageMeta({ layout: false })

const authStore = useAuthStore()
const route = useRoute()
const inviteToken = (route.query.invite as string) || null

const form = reactive({
  email: '',
  username: '',
  display_name: '',
  password: '',
})

const loading = ref(false)
const errorMessage = ref('')
const success = ref(false)

async function handleRegister(): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  if (form.password.length < 12) {
    errorMessage.value = $t('auth.errors.weakPassword')
    loading.value = false
    return
  }
  if (form.username.length < 3) {
    errorMessage.value = $t('auth.errors.usernameShort')
    loading.value = false
    return
  }

  try {
    await authStore.register({
      ...form,
      ...(inviteToken ? { invite_token: inviteToken } : {}),
    })

    success.value = true
    setTimeout(() => { navigateTo('/app', { replace: true }) }, 1500)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}
</script>
