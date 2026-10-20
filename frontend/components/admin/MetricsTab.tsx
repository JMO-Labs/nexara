"use client";
/**
 * @file components/admin/MetricsTab.tsx
 * @brief Admin metrics display with community, system, and WAF stats.
 */
import { useAdminMetrics } from "@/hooks/useAdmin";
import Stack from "@mui/joy/Stack";
import Grid from "@mui/joy/Grid";
import Card from "@mui/joy/Card";
import Typography from "@mui/joy/Typography";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";

function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIdx = 0;
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024;
    unitIdx += 1;
  }
  return `${size.toFixed(1)} ${units[unitIdx]}`;
}

function formatSeconds(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${days}d ${hours}h`;
}

/**
 * @brief Displays a metric card with label and value.
 */
function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <Card variant="soft">
      <Stack spacing={1}>
        <Typography level="body-sm" color="neutral">
          {label}
        </Typography>
        <Typography level="h2" component="div">
          {value}
        </Typography>
      </Stack>
    </Card>
  );
}

export function MetricsTab() {
  const { data: metrics, isLoading, error } = useAdminMetrics();

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
        Failed to load metrics
      </Alert>
    );
  }

  if (!metrics) return null;

  return (
    <Stack spacing={3}>
      {/* Key Performance Indicators */}
      <div>
        <Typography level="title-md" component="h3" sx={{ mb: 1.5 }}>
          Key Performance Indicators
        </Typography>
        <Grid container spacing={1.5}>
          <Grid xs={6} sm={3} md={3}>
            <MetricCard
              label="Total Users"
              value={metrics.community.users_total}
            />
          </Grid>
          <Grid xs={6} sm={3} md={3}>
            <MetricCard
              label="Active (30d)"
              value={metrics.community.users_active_30d}
            />
          </Grid>
          <Grid xs={6} sm={3} md={3}>
            <MetricCard
              label="Posts (7d)"
              value={metrics.community.posts_last_7d}
            />
          </Grid>
          <Grid xs={6} sm={3} md={3}>
            <MetricCard
              label="Storage"
              value={formatBytes(metrics.community.media_storage_bytes)}
            />
          </Grid>
        </Grid>
      </div>

      {/* Extended Metrics: 2-col on desktop */}
      <Grid container spacing={2}>
        <Grid xs={12} md={6}>
          <div>
            <Typography level="title-sm" component="h4" sx={{ mb: 1.5 }}>
              Community
            </Typography>
            <Grid container spacing={1.5}>
              <Grid xs={6} sm={6}>
                <MetricCard
                  label="Online Now"
                  value={metrics.community.users_online_now}
                />
              </Grid>
              <Grid xs={6} sm={6}>
                <MetricCard
                  label="Total Posts"
                  value={metrics.community.posts_total}
                />
              </Grid>
              <Grid xs={6} sm={6}>
                <MetricCard
                  label="Media Files"
                  value={metrics.community.media_files}
                />
              </Grid>
            </Grid>
          </div>
        </Grid>

        <Grid xs={12} md={6}>
          <div>
            <Typography level="title-sm" component="h4" sx={{ mb: 1.5 }}>
              System
            </Typography>
            <Grid container spacing={1.5}>
              <Grid xs={6} sm={6}>
                <MetricCard label="Version" value={metrics.system.version} />
              </Grid>
              <Grid xs={6} sm={6}>
                <MetricCard
                  label="Uptime"
                  value={formatSeconds(metrics.system.uptime_seconds)}
                />
              </Grid>
              {metrics.system.db_size_bytes && (
                <Grid xs={6} sm={6}>
                  <MetricCard
                    label="DB Size"
                    value={formatBytes(metrics.system.db_size_bytes)}
                  />
                </Grid>
              )}
              {metrics.system.valkey_memory_bytes && (
                <Grid xs={6} sm={6}>
                  <MetricCard
                    label="Valkey Memory"
                    value={formatBytes(metrics.system.valkey_memory_bytes)}
                  />
                </Grid>
              )}
              {metrics.system.celery_queue_depth !== undefined && (
                <Grid xs={6} sm={6}>
                  <MetricCard
                    label="Celery Queue"
                    value={metrics.system.celery_queue_depth ?? 0}
                  />
                </Grid>
              )}
            </Grid>
          </div>
        </Grid>
      </Grid>

      {/* Security */}
      <div>
        <Typography level="title-sm" component="h4" sx={{ mb: 1.5 }}>
          Security (WAF)
        </Typography>
        <Grid container spacing={1.5}>
          <Grid xs={6} sm={3} md={3}>
            <MetricCard label="Blocks Today" value={metrics.waf.blocks_today} />
          </Grid>
          {Object.entries(metrics.waf.blocks_by_reason).map(
            ([reason, count]) => (
              <Grid key={reason} xs={6} sm={3} md={3}>
                <MetricCard label={`${reason} blocks`} value={count} />
              </Grid>
            ),
          )}
        </Grid>
      </div>
    </Stack>
  );
}
