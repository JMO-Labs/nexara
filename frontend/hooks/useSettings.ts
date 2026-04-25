/**
 * @file hooks/useSettings.ts
 * @brief TanStack Query hooks for user settings: profile, notifications, appearance.
 */
'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import {
  getSettings,
  updateSettings,
  getNotificationPrefs,
  updateNotificationPrefs,
  updateProfile,
  updateEmail,
  type NotificationPreferences,
  type ProfileUpdate,
  type UserSettingsUpdate,
} from '@/lib/api/settings';
import { useMutationWithToast } from './useMutationWithToast';

/**
 * @brief Fetch user settings (theme, locale, notifications).
 * @return Query result with UserSettings data.
 */
export function useUserSettings() {
  return useQuery({
    queryKey: qk.settings.profile(),
    queryFn: getSettings,
    staleTime: 60_000,
  });
}

/**
 * @brief Fetch notification preferences.
 * @return Query result with NotificationPreferences data.
 */
export function useNotificationPrefs() {
  return useQuery({
    queryKey: qk.settings.notifications(),
    queryFn: getNotificationPrefs,
    staleTime: 60_000,
  });
}

/**
 * @brief Mutation to update settings (theme, locale).
 * @return Mutation with success toast.
 */
export function useUpdateSettings() {
  const qc = useQueryClient();

  return useMutationWithToast({
    mutationFn: (body: Partial<UserSettingsUpdate>) => updateSettings(body),
    successKey: 'toasts.settings.saved',
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.settings.profile() });
    },
  });
}

/**
 * @brief Mutation to update profile information.
 * @return Mutation with success toast.
 */
export function useUpdateProfile() {
  const qc = useQueryClient();

  return useMutationWithToast({
    mutationFn: (body: Partial<ProfileUpdate>) => updateProfile(body),
    successKey: 'toasts.settings.saved',
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.settings.profile() });
    },
  });
}

/**
 * @brief Mutation to update email address.
 * @return Mutation with success toast.
 */
export function useUpdateEmail() {
  const qc = useQueryClient();

  return useMutationWithToast({
    mutationFn: (email: string) => updateEmail(email),
    successKey: 'toasts.settings.saved',
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.settings.profile() });
    },
  });
}

/**
 * @brief Mutation to update notification preferences.
 * @return Mutation with success toast.
 */
export function useUpdateNotificationPrefs() {
  const qc = useQueryClient();

  return useMutationWithToast({
    mutationFn: (body: Partial<NotificationPreferences>) =>
      updateNotificationPrefs(body),
    successKey: 'toasts.settings.saved',
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.settings.notifications() });
    },
  });
}
