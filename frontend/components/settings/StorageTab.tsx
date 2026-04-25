'use client';
/**
 * @file components/settings/StorageTab.tsx
 * @brief Storage settings tab: placeholder for storage usage info.
 */
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { EmptyState } from '@/components/ui/EmptyState';

export function StorageTab() {
  return (
    <Stack spacing={3}>
      <div>
        <Typography level="h3">Storage</Typography>
        <Typography level="body-sm" color="neutral">
          View and manage your account storage.
        </Typography>
      </div>

      <EmptyState
        title="Storage Usage Coming Soon"
        description="Storage usage analytics will be available in a future update."
      />
    </Stack>
  );
}
