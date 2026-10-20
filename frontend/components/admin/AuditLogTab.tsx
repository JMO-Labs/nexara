"use client";
/**
 * @file components/admin/AuditLogTab.tsx
 * @brief Paginated audit log viewer with filter rail.
 */
import { useState } from "react";
import { useAuditLog } from "@/hooks/useAdmin";
import Stack from "@mui/joy/Stack";
import Grid from "@mui/joy/Grid";
import Card from "@mui/joy/Card";
import Table from "@mui/joy/Table";
import Typography from "@mui/joy/Typography";
import Button from "@mui/joy/Button";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";
import Input from "@mui/joy/Input";
import { format } from "date-fns";
import { ChevronRightIcon } from "@heroicons/react/24/outline";

export function AuditLogTab() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState<string>("");
  const [actorFilter, setActorFilter] = useState<string>("");

  const {
    data: auditLog,
    isLoading,
    error,
  } = useAuditLog({
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

  // Filter items
  const filtered = auditLog.items.filter((entry) => {
    if (
      actionFilter &&
      !entry.action.toLowerCase().includes(actionFilter.toLowerCase())
    ) {
      return false;
    }
    if (
      actorFilter &&
      !(entry.actor_display_name || "")
        .toLowerCase()
        .includes(actorFilter.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  return (
    <Grid container spacing={2}>
      {/* Filter Rail: 3/12 on desktop, hidden on mobile */}
      <Grid xs={0} md={3} sx={{ display: { xs: "none", md: "flex" } }}>
        <Card variant="outlined" sx={{ width: "100%" }}>
          <Stack spacing={1.5}>
            <Typography level="title-sm">Filters</Typography>
            <Stack spacing={1}>
              <Input
                placeholder="Filter by action"
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                size="sm"
              />
              <Input
                placeholder="Filter by actor"
                value={actorFilter}
                onChange={(e) => setActorFilter(e.target.value)}
                size="sm"
              />
              {(actionFilter || actorFilter) && (
                <Button
                  variant="plain"
                  size="sm"
                  onClick={() => {
                    setActionFilter("");
                    setActorFilter("");
                  }}
                >
                  Clear Filters
                </Button>
              )}
            </Stack>
          </Stack>
        </Card>
      </Grid>

      {/* Log Stream: 9/12 on desktop, full width on mobile */}
      <Grid xs={12} md={9}>
        <Card variant="outlined">
          <Table
            stripe="odd"
            hoverRow
            sx={{
              "--TableCell-paddingX": "0.75rem",
              "--TableCell-paddingY": "0.375rem",
              fontSize: "0.85rem",
            }}
          >
            <thead>
              <tr>
                <th>Action</th>
                <th>Actor</th>
                <th>Target</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map((entry) => (
                  <tr key={entry.id}>
                    <td>
                      <Typography level="body-xs">{entry.action}</Typography>
                    </td>
                    <td>
                      <Typography level="body-xs">
                        {entry.actor_display_name || "(system)"}
                      </Typography>
                    </td>
                    <td>
                      <Typography level="body-xs">
                        {entry.target_display || entry.target_type || "-"}
                      </Typography>
                    </td>
                    <td>
                      <Typography level="body-xs" sx={{ whiteSpace: "nowrap" }}>
                        {format(new Date(entry.created_at), "MMM d HH:mm")}
                      </Typography>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4}>
                    <Typography level="body-xs" color="neutral">
                      No entries match filters
                    </Typography>
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card>

        {auditLog.has_more && (
          <Stack direction="row" justifyContent="center" sx={{ mt: 2 }}>
            <Button
              size="sm"
              onClick={() => setCursor(auditLog.next_cursor)}
              endDecorator={<ChevronRightIcon width={16} height={16} />}
            >
              Load More
            </Button>
          </Stack>
        )}
      </Grid>
    </Grid>
  );
}
