'use client';
/**
 * @file components/settings/SettingsTabs.tsx
 * @brief Settings page with tabs: account, profile, notifications, appearance, storage.
 *        Deep-linkable via ?tab= query parameter.
 */
import { useSearchParams, useRouter } from 'next/navigation';
import Sheet from '@mui/joy/Sheet';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Tabs, TabList, Tab, TabPanel } from '@/components/ui/Tabs';
import { AccountTab } from './AccountTab';
import { ProfileTab } from './ProfileTab';
import { NotificationsTab } from './NotificationsTab';
import { AppearanceTab } from './AppearanceTab';
import { StorageTab } from './StorageTab';

const TABS = [
  { id: 'account', label: 'Account', icon: 'person' },
  { id: 'profile', label: 'Profile', icon: 'edit' },
  { id: 'notifications', label: 'Notifications', icon: 'notifications' },
  { id: 'appearance', label: 'Appearance', icon: 'palette' },
  { id: 'storage', label: 'Storage', icon: 'storage' },
];

export function SettingsTabs() {
  const router = useRouter();
  const params = useSearchParams();
  const currentTab = params.get('tab') || 'account';

  const handleTabChange = (_: unknown, value: string | number | null) => {
    if (value) {
      router.replace(`?tab=${value}`);
    }
  };

  return (
    <Sheet
      sx={{
        flex: 1,
        width: '100%',
        mx: 'auto',
        px: { xs: 2, md: 6 },
        py: { xs: 2, md: 3 },
        borderRadius: { xs: 'sm', md: 'md' },
      }}
    >
      <Stack spacing={3}>
        <div>
          <Typography level="h1" component="h1">
            Settings
          </Typography>
          <Typography level="body-md" color="neutral">
            Manage your account preferences and settings.
          </Typography>
        </div>

        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          sx={{
            '--Tabs-gap': '0px',
            '--Tab-minHeight': '48px',
          }}
        >
          <TabList
            disableUnderline
            sx={{
              borderBottom: '1px solid',
              borderColor: 'divider',
              display: 'flex',
              overflow: 'auto',
            }}
          >
            {TABS.map(({ id, label }) => (
              <Tab
                key={id}
                value={id}
                sx={{
                  flexShrink: 0,
                  px: 2,
                  py: 1.5,
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.05)',
                  },
                }}
              >
                {label}
              </Tab>
            ))}
          </TabList>

          {TABS.map(({ id }) => (
            <TabPanel key={id} value={id} sx={{ px: 0, py: 3 }}>
              {id === 'account' && <AccountTab />}
              {id === 'profile' && <ProfileTab />}
              {id === 'notifications' && <NotificationsTab />}
              {id === 'appearance' && <AppearanceTab />}
              {id === 'storage' && <StorageTab />}
            </TabPanel>
          ))}
        </Tabs>
      </Stack>
    </Sheet>
  );
}
