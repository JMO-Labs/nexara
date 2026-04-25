'use client';
/**
 * @file components/settings/NotificationsTab.tsx
 * @brief Notifications settings tab: grid of toggles per notif type × channel.
 */
import { useCallback, useState } from 'react';
import Stack from '@mui/joy/Stack';
import Table from '@mui/joy/Table';
import Typography from '@mui/joy/Typography';
import Switch from '@mui/joy/Switch';
import FormLabel from '@mui/joy/FormLabel';
import Skeleton from '@mui/joy/Skeleton';
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
    <Stack spacing={3}>
      <PushSubscriptionRow />
      <div>
        <Typography level="h3">Notification Preferences</Typography>
        <Typography level="body-sm" color="neutral">
          Choose how you receive notifications.
        </Typography>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <Table>
          <thead>
            <tr>
              <th style={{ width: '150px' }}>Type</th>
              <th style={{ width: '150px' }}>In-App</th>
              <th style={{ width: '150px' }}>Email</th>
            </tr>
          </thead>
          <tbody>
            {notifTypes.map(({ key, label }) => (
              <tr key={key}>
                <td>{label}</td>
                <td>
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
                </td>
                <td>
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
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>

      <Stack direction="row" spacing={2} alignItems="center">
        <FormLabel>Mute all email notifications</FormLabel>
        <Switch
          checked={prefs.mute_all_email}
          onChange={(e) => handleToggle('mute_all_email', e.target.checked)}
        />
      </Stack>
    </Stack>
  );
}
