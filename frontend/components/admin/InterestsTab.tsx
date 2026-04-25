'use client';
/**
 * @file components/admin/InterestsTab.tsx
 * @brief Read-only interest analytics display.
 */
import { useQuery } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import { getInterestAnalytics } from '@/lib/api/interests';
import Stack from '@mui/joy/Stack';
import Card from '@mui/joy/Card';
import Table from '@mui/joy/Table';
import Typography from '@mui/joy/Typography';
import CircularProgress from '@mui/joy/CircularProgress';
import Alert from '@mui/joy/Alert';

export function InterestsTab() {
  const { data: analytics, isLoading, error } = useQuery({
    queryKey: qk.admin.interestsAnalytics(),
    queryFn: getInterestAnalytics,
    staleTime: 5 * 60 * 1000,
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
        Failed to load interest analytics
      </Alert>
    );
  }

  if (!analytics || analytics.length === 0) {
    return (
      <Alert color="primary" variant="soft">
        No interest data available yet
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
              <th>Category</th>
              <th>Value</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {analytics.map((item, idx) => (
              <tr key={`${item.category_slug}-${item.value}-${idx}`}>
                <td>
                  <Typography level="body-sm">
                    {item.category_slug}
                  </Typography>
                </td>
                <td>
                  <Typography level="body-sm">{item.value}</Typography>
                </td>
                <td>
                  <Typography level="body-sm">{item.count}</Typography>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </Stack>
  );
}
