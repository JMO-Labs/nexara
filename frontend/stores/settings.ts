/**
 * @file stores/settings.ts
 * @brief Pinia store for user settings management.
 *
 * Manages user settings (notification preferences, theme, locale),
 * profile updates, and notification preference updates. Uses useApi()
 * for all HTTP calls to /settings/ endpoints.
 */

import { ref } from "vue";
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";
import { useAuthStore } from "~/stores/auth";
import type { UserSettingsResponse } from "~/types/api";

/** @brief Profile update payload for PUT /settings/profile. */
export interface ProfileUpdatePayload {
  display_name?: string;
  bio?: string;
  location?: string;
  website_url?: string;
  title?: string;
}

/** @brief Notification preferences payload for PUT /settings/notifications. */
export interface NotificationPreferencesPayload {
  notif_mention_inapp?: boolean;
  notif_mention_email?: boolean;
  notif_comment_inapp?: boolean;
  notif_comment_email?: boolean;
  notif_reaction_inapp?: boolean;
  notif_reaction_email?: boolean;
  notif_new_post_inapp?: boolean;
  notif_new_post_email?: boolean;
  notif_system_inapp?: boolean;
  notif_system_email?: boolean;
  notif_invite_accepted_inapp?: boolean;
  notif_invite_accepted_email?: boolean;
  mute_all_email?: boolean;
}

export const useSettingsStore = defineStore("settings", () => {
  /** @brief Current user settings from the API. */
  const settings = ref<UserSettingsResponse | null>(null);

  /** @brief Whether a fetch or update operation is in progress. */
  const loading = ref(false);

  /**
   * @brief Fetch user settings from GET /settings/.
   * @throws Error if the request fails.
   */
  async function fetchSettings(): Promise<void> {
    loading.value = true;
    try {
      const api = useApi();
      settings.value = await api.get<UserSettingsResponse>("/settings/");
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Update full settings via PUT /settings/.
   * @param data - Partial settings to merge and send.
   * @throws Error if the request fails.
   */
  async function updateSettings(
    data: Partial<UserSettingsResponse>,
  ): Promise<void> {
    loading.value = true;
    try {
      const api = useApi();
      const updated = await api.put<UserSettingsResponse>("/settings/", {
        ...settings.value,
        ...data,
      });
      settings.value = updated;
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Update profile via PUT /settings/profile.
   * @param data - Profile fields to update.
   * @throws Error if the request fails.
   */
  async function updateProfile(data: ProfileUpdatePayload): Promise<void> {
    loading.value = true;
    try {
      const api = useApi();
      await api.put("/settings/profile", data);
      await useAuthStore().fetchUser();
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Update notification preferences via PUT /settings/notifications.
   * @param data - Notification preference fields to update.
   * @throws Error if the request fails.
   */
  async function updateNotificationPreferences(
    data: NotificationPreferencesPayload,
  ): Promise<void> {
    loading.value = true;
    try {
      const api = useApi();
      const updated = await api.put<UserSettingsResponse>(
        "/settings/notifications",
        {
          ...settings.value,
          ...data,
        },
      );
      settings.value = updated;
    } finally {
      loading.value = false;
    }
  }

  return {
    settings,
    loading,
    fetchSettings,
    updateSettings,
    updateProfile,
    updateNotificationPreferences,
  };
});
