<!--
  @file pages/app/settings/profile.vue
  @brief Profile editing tab in settings.

  Form fields: display_name, bio, location, website_url, pronouns.
  Submit calls settingsStore.updateProfile() and shows success toast.
-->
<template>
  <div class="rounded-lg border border-border bg-card p-6">
    <form
      class="space-y-4"
      @submit.prevent="handleSubmit"
    >
      <div>
        <label
          for="display_name"
          class="mb-1 block text-sm font-medium text-foreground"
        >
          {{ $t('settings.displayName') }}
        </label>
        <input
          id="display_name"
          v-model="form.display_name"
          type="text"
          class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
        >
      </div>

      <div>
        <label
          for="bio"
          class="mb-1 block text-sm font-medium text-foreground"
        >
          {{ $t('settings.bio') }}
        </label>
        <textarea
          id="bio"
          v-model="form.bio"
          rows="4"
          class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
        />
      </div>

      <div>
        <label
          for="location"
          class="mb-1 block text-sm font-medium text-foreground"
        >
          {{ $t('settings.location') }}
        </label>
        <input
          id="location"
          v-model="form.location"
          type="text"
          class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
        >
      </div>

      <div>
        <label
          for="website_url"
          class="mb-1 block text-sm font-medium text-foreground"
        >
          {{ $t('settings.websiteUrl') }}
        </label>
        <input
          id="website_url"
          v-model="form.website_url"
          type="url"
          class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
        >
      </div>

      <div>
        <label
          for="pronouns"
          class="mb-1 block text-sm font-medium text-foreground"
        >
          {{ $t('settings.pronouns') }}
        </label>
        <input
          id="pronouns"
          v-model="form.pronouns"
          type="text"
          class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
        >
      </div>

      <button
        type="submit"
        :disabled="settingsStore.loading"
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {{ settingsStore.loading ? $t('common.loading') : $t('common.save') }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Profile form with auth store sync and success toast.
 */
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settings'
import { useAuthStore } from '~/stores/auth'
import { useUiStore } from '~/stores/ui'

const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const { t: $t } = useI18n()

const form = ref({
  display_name: '',
  bio: '',
  location: '',
  website_url: '',
  pronouns: '',
})

onMounted(() => {
  const u = authStore.user
  if (u) {
    form.value = {
      display_name: u.display_name ?? '',
      bio: u.bio ?? '',
      location: u.location ?? '',
      website_url: u.website_url ?? '',
      pronouns: u.pronouns ?? '',
    }
  }
})

async function handleSubmit(): Promise<void> {
  try {
    await settingsStore.updateProfile({
      display_name: form.value.display_name,
      bio: form.value.bio,
      location: form.value.location,
      website_url: form.value.website_url,
      pronouns: form.value.pronouns,
    })
    uiStore.showToast({ type: 'success', message: $t('settings.profileSaved') })
  } catch (error) {
    uiStore.showToast({
      type: 'error',
      message: error instanceof Error ? error.message : $t('common.error'),
    })
  }
}
</script>
