<!--
  @file pages/app/settings/account.vue
  @brief Account settings tab.

  Shows current email and username (read-only). Placeholder for
  email change flow to be implemented later.
-->
<template>
  <div class="rounded-lg border border-border bg-card p-6">
    <div class="space-y-4">
      <div>
        <label class="mb-1 block text-sm font-medium text-muted-foreground">
          {{ $t('settings.email') }}
        </label>
        <p class="text-foreground">
          {{ authStore.user?.email ?? '—' }}
        </p>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ $t('settings.changeEmail') }} {{ $t('common.comingSoon') }}
        </p>
      </div>

      <div>
        <label class="mb-1 block text-sm font-medium text-muted-foreground">
          {{ $t('settings.username') }}
        </label>
        <p class="text-foreground">
          {{ authStore.user?.username ?? '—' }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Account settings with read-only email and username.
 */
import { useAuthStore } from '~/stores/auth'

const authStore = useAuthStore()
</script>
