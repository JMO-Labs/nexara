'use client';
/**
 * @file components/settings/AppearanceTab.tsx
 * @brief Appearance settings tab with two-column layout: theme and locale.
 */
import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import Typography from '@mui/joy/Typography';
import { Card, SettingsRow, Select } from '@/components/ui';
import { useUpdateSettings, useUserSettings } from '@/hooks/useSettings';

export function AppearanceTab() {
  const { theme, setTheme } = useTheme();
  const { data: settings } = useUserSettings();
  const { mutate, isPending } = useUpdateSettings();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // next-themes SSR-safe mount detection — setState in effect is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  if (!mounted || !settings) {
    return <Typography>Loading appearance settings...</Typography>;
  }

  const handleThemeChange = (value: string) => {
    setTheme(value);
    mutate({ theme: value as 'system' | 'light' | 'dark' });
  };

  const handleLocaleChange = (value: string) => {
    mutate({ locale: value });
  };

  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Card variant="outlined">
        <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
          Appearance
        </Typography>

        <SettingsRow
          label="Theme"
          description="Choose between light, dark, or system preference."
        >
          <Stack spacing={1} sx={{ width: '100%' }}>
            <FormControl>
              <FormLabel>Theme</FormLabel>
              <Select
                value={theme || 'system'}
                onChange={(_e, newValue) => handleThemeChange(newValue || 'system')}
                disabled={isPending}
              >
                <option value="system">System</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </Select>
            </FormControl>
          </Stack>
        </SettingsRow>

        <SettingsRow
          label="Language"
          description="Select your preferred language."
        >
          <Stack spacing={1} sx={{ width: '100%' }}>
            <FormControl>
              <FormLabel>Language</FormLabel>
              <Select
                value={settings.locale || 'en-US'}
                onChange={(_e, newValue) => handleLocaleChange(newValue || 'en-US')}
                disabled={isPending}
              >
                <option value="en-US">English (US)</option>
              </Select>
            </FormControl>
          </Stack>
        </SettingsRow>
      </Card>
    </Stack>
  );
}
