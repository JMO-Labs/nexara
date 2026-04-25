'use client';
/**
 * @file components/admin/AuditLogTab.tsx
 * @brief Paginated audit log viewer.
 */
import { useState } from 'react';
import { useAuditLog } from '@/hooks/useAdmin';
import Stack from '@mui/joy/Stack';
import Card from '@mui/joy/Card';
import Table from '@mui/joy/Table';
import Typography from '@mui/joy/Typography';
import Button from '@mui/joy/Button';
import CircularProgress from '@mui/joy/CircularProgress';
import Alert from '@mui/joy/Alert';
import { format } from 'date-fns';
import { ChevronRightIcon } from '@heroicons/react/24/outline';

export function AuditLogTab() {
  const [cursor, setCursor] = useState<string | null>(null);

  const { data: auditLog, isLoading, error } = useAuditLog({
    limit: 50,
    cursor,
  });

  if (isLoading) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="danger" variant="soft">
        Failed to load audit log
      </Alert>
    );
  }

  if (!auditLog || auditLog.items.length === 0) {
    return (
      <Alert color="primary" variant="soft">
        No audit log entries
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      <Card variant="outlined">
        <Table
          stripe="odd"
          hoverRow
          sx={{
            '--TableCell-paddingX': '1rem',
            '--TableCell-paddingY': '0.5rem',
          }}
        >
          <thead>
            <tr>
              <th>Action</th>
              <th>Actor</th>
              <th>Target</th>
              <th>Timestamp</th>
              <th>IP Address</th>
            </tr>
          </thead>
          <tbody>
            {auditLog.items.map((entry) => (
              <tr key={entry.id}>
                <td>
                  <Typography level="body-sm">{entry.action}</Typography>
                </td>
                <td>
                  <Typography level="body-sm">
                    {entry.actor_display_name || '(system)'}
                  </Typography>
                </td>
                <td>
                  <Typography level="body-sm">
                    {entry.target_display || entry.target_type || '-'}
                  </Typography>
                </td>
                <td>
                  <Typography level="body-sm" sx={{ whiteSpace: 'nowrap' }}>
                    {format(new Date(entry.created_at), 'MMM d, yyyy HH:mm:ss')}
                  </Typography>
                </td>
                <td>
                  <Typography level="body-sm">{entry.ip_address || '-'}</Typography>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {auditLog.has_more && (
        <Stack direction="row" justifyContent="center">
          <Button
            onClick={() => setCursor(auditLog.next_cursor)}
            endDecorator={<ChevronRightIcon width={16} height={16} />}
          >
            Load More
          </Button>
        </Stack>
      )}
    </Stack>
  );
}
