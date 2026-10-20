"use client";
/**
 * @file components/admin/InterestsTab.tsx
 * @brief Interest analytics display with chip-style categories.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getInterestAnalytics } from "@/lib/api/interests";
import Stack from "@mui/joy/Stack";
import Card from "@mui/joy/Card";
import Chip from "@mui/joy/Chip";
import Typography from "@mui/joy/Typography";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";

export function InterestsTab() {
  const {
    data: analytics,
    isLoading,
    error,
  } = useQuery({
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

  // Group by category
  const grouped = analytics.reduce(
    (acc, item) => {
      if (!acc[item.category_slug]) acc[item.category_slug] = [];
      acc[item.category_slug].push(item);
      return acc;
    },
    {} as Record<string, typeof analytics>,
  );

  return (
    <Stack spacing={2}>
      {Object.entries(grouped).map(([category, items]) => (
        <Card key={category} variant="outlined">
          <Stack spacing={1}>
            <Typography level="title-sm" sx={{ textTransform: "capitalize" }}>
              {category}
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              flexWrap="wrap"
              sx={{
                gap: 1,
              }}
            >
              {items
                .sort((a, b) => b.count - a.count)
                .map((item, idx) => (
                  <Chip
                    key={`${item.value}-${idx}`}
                    variant="soft"
                    size="md"
                    endDecorator={
                      <Typography level="body-xs" sx={{ ml: 0.5 }}>
                        {item.count}
                      </Typography>
                    }
                  >
                    {item.value}
                  </Chip>
                ))}
            </Stack>
          </Stack>
        </Card>
      ))}
    </Stack>
  );
}
