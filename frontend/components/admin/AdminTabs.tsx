'use client';
/**
 * @file components/admin/AdminTabs.tsx
 * @brief Main admin panel with tabbed interface. Deep-linkable via ?tab=.
 *        Enforces admin role requirement.
 */
import { useSearchParams } from 'next/navigation';
import { useSession } from '@/stores/session';
import Tabs from '@mui/joy/Tabs';
import TabList from '@mui/joy/TabList';
import Tab from '@mui/joy/Tab';
import TabPanel from '@mui/joy/TabPanel';
import Stack from '@mui/joy/Stack';
import Alert from '@mui/joy/Alert';
import { AnimatePresence, motion } from 'framer-motion';
import { tabPanelVariants } from '@/components/ui/motion';
import { MetricsTab } from './MetricsTab';
import { UsersTab } from './UsersTab';
import { InvitesTab } from './InvitesTab';
import { SsoTab } from './SsoTab';
import { InterestsTab } from './InterestsTab';
import { AuditLogTab } from './AuditLogTab';
import { AdminSettingsTab } from './AdminSettingsTab';
import { PromptsTab } from './PromptsTab';

const TABS = [
  { id: 'metrics', label: 'Metrics' },
  { id: 'users', label: 'Users' },
  { id: 'invites', label: 'Invites' },
  { id: 'sso', label: 'SSO' },
  { id: 'interests', label: 'Interests' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'audit-log', label: 'Audit Log' },
  { id: 'settings', label: 'Settings' },
];

export function AdminTabs() {
  const searchParams = useSearchParams();
  const user = useSession((s) => s.user);

  const selectedTab = searchParams.get('tab') || 'metrics';

  // Check admin role
  if (!user || user.role !== 'admin') {
    return (
      <Alert color="warning" variant="soft">
        Admin access required. Your current role is: {user?.role || 'unauthenticated'}
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      <Tabs
        defaultValue={selectedTab}
        sx={{ bgcolor: 'transparent' }}
      >
        <TabList
          sx={{
            '--TabList-gap': '0px',
            '--List-padding': '0px',
            '--ListDivider-gap': '0px',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {TABS.map((tab) => (
            <Tab
              key={tab.id}
              value={tab.id}
              component="a"
              href={`/app/admin?tab=${tab.id}`}
              data-tour={
                tab.id === 'invites'
                  ? 'admin-invites'
                  : tab.id === 'users'
                    ? 'admin-users'
                    : tab.id === 'sso'
                      ? 'admin-sso'
                      : undefined
              }
              sx={{
                '&[aria-selected="true"]': {
                  fontWeight: 'bold',
                  borderBottomColor: 'primary.main',
                },
              }}
            >
              {tab.label}
            </Tab>
          ))}
        </TabList>

        <AnimatePresence mode="wait">
          {TABS.map((tab) => (
            <TabPanel key={tab.id} value={tab.id} sx={{ px: 0, py: 3 }}>
              <motion.div
                key={`panel-${tab.id}`}
                variants={tabPanelVariants}
                initial="initial"
                animate="animate"
                exit="exit"
              >
                {tab.id === 'metrics' && <MetricsTab />}
                {tab.id === 'users' && <UsersTab />}
                {tab.id === 'invites' && <InvitesTab />}
                {tab.id === 'sso' && <SsoTab />}
                {tab.id === 'interests' && <InterestsTab />}
                {tab.id === 'prompts' && <PromptsTab />}
                {tab.id === 'audit-log' && <AuditLogTab />}
                {tab.id === 'settings' && <AdminSettingsTab />}
              </motion.div>
            </TabPanel>
          ))}
        </AnimatePresence>
      </Tabs>
    </Stack>
  );
}
