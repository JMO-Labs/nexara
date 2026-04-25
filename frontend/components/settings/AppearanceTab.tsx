'use client';
/**
 * @file components/settings/AppearanceTab.tsx
 * @brief Appearance settings tab: theme and locale selectors.
 */
import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import Typography from '@mui/joy/Typography';
import Select from '@/components/ui/Select';
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
    <Stack spacing={3}>
      <div>
        <Typography level="h3">Appearance</Typography>
        <Typography level="body-sm" color="neutral">
          Customize how the app looks and feels.
        </Typography>
      </div>

      <Stack spacing={2}>
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
    </Stack>
  );
}
