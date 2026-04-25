'use client';
/**
 * @file components/settings/NotificationsTab.tsx
 * @brief Notifications settings tab with two-column toggle grid.
 */
import { useCallback, useState } from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Switch from '@mui/joy/Switch';
import Skeleton from '@mui/joy/Skeleton';
import { Card, SettingsRow } from '@/components/ui';
import {
  useNotificationPrefs,
  useUpdateNotificationPrefs,
} from '@/hooks/useSettings';
import type { NotificationPreferences } from '@/lib/api/settings';
import { PushSubscriptionRow } from './PushSubscriptionRow';

export function NotificationsTab() {
  const { data: prefs, isLoading } = useNotificationPrefs();
  const { mutate } = useUpdateNotificationPrefs();
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  const handleToggle = useCallback(
    (key: keyof NotificationPreferences, value: boolean) => {
      if (debounceTimer) clearTimeout(debounceTimer);
      const timer = setTimeout(() => {
        mutate({ [key]: value });
      }, 400);
      setDebounceTimer(timer);
    },
    [debounceTimer, mutate]
  );

  if (isLoading) {
    return <Skeleton width="100%" height={200} />;
  }

  if (!prefs) {
    return <Typography>No notification preferences loaded.</Typography>;
  }

  const notifTypes = [
    { key: 'mention', label: 'Mention' },
    { key: 'comment', label: 'Comment' },
    { key: 'reaction', label: 'Reaction' },
    { key: 'new_post', label: 'New Post' },
    { key: 'system', label: 'System' },
    { key: 'invite_accepted', label: 'Invite Accepted' },
  ];

  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <PushSubscriptionRow />

      <Card variant="outlined">
        <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
          Notification Preferences
        </Typography>

        {notifTypes.map(({ key, label }) => (
          <SettingsRow
            key={key}
            label={label}
            description="Receive notifications via these channels."
          >
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ pt: 0.5 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ flex: 1 }}>
                <Switch
                  checked={
                    prefs[`notif_${key}_inapp` as keyof NotificationPreferences] as boolean
                  }
                  onChange={(e) =>
                    handleToggle(
                      `notif_${key}_inapp` as keyof NotificationPreferences,
                      e.target.checked
                    )
                  }
                />
                <Typography level="body-sm">In-App</Typography>
              </Stack>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ flex: 1 }}>
                <Switch
                  checked={
                    prefs[`notif_${key}_email` as keyof NotificationPreferences] as boolean
                  }
                  onChange={(e) =>
                    handleToggle(
                      `notif_${key}_email` as keyof NotificationPreferences,
                      e.target.checked
                    )
                  }
                />
                <Typography level="body-sm">Email</Typography>
              </Stack>
            </Stack>
          </SettingsRow>
        ))}

        <SettingsRow
          label="Mute All Email"
          description="Disable all email notifications at once."
        >
          <Switch
            checked={prefs.mute_all_email}
            onChange={(e) => handleToggle('mute_all_email', e.target.checked)}
          />
        </SettingsRow>
      </Card>
    </Stack>
  );
}
