'use client';
/**
 * @file components/settings/StorageTab.tsx
 * @brief Storage settings tab with two-column layout.
 */
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Card, EmptyState } from '@/components/ui';

export function StorageTab() {
  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Card variant="outlined">
        <Typography level="title-md" component="h2" sx={{ mb: 2 }}>
          Storage
        </Typography>

        <EmptyState
          title="Storage Usage Coming Soon"
          description="Storage usage analytics will be available in a future update."
        />
      </Card>
    </Stack>
  );
}
