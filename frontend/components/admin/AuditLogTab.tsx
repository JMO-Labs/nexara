"use client";
/**
 * @file components/admin/AuditLogTab.tsx
 * @brief Paginated audit log viewer with filter rail.
 */
import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { format } from "date-fns";
import { useAuditLog } from "@/hooks/useAdmin";
import { Button, Card, Input } from "@/components/ui";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/shadcn/table";
import { AdminLoading, AdminNotice, stackTable } from "./AdminState";

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

  if (isLoading) return <AdminLoading />;

  if (error) {
    return <AdminNotice tone="error">Failed to load audit log</AdminNotice>;
  }

  if (!auditLog || auditLog.items.length === 0) {
    return <AdminNotice>No audit log entries</AdminNotice>;
  }

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
    <div className="grid gap-4 md:grid-cols-12">
      <Card className="flex flex-col gap-3 p-4 md:col-span-3 md:self-start">
        <h3 className="text-sm font-semibold">Filters</h3>
        <Input
          label="Action"
          placeholder="Filter by action"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        />
        <Input
          label="Actor"
          placeholder="Filter by actor"
          value={actorFilter}
          onChange={(e) => setActorFilter(e.target.value)}
        />
        {(actionFilter || actorFilter) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setActionFilter("");
              setActorFilter("");
            }}
          >
            Clear filters
          </Button>
        )}
      </Card>

      <div className="md:col-span-9">
        <Card className="p-2">
          <Table>
            <TableHeader className={stackTable.head}>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length > 0 ? (
                filtered.map((entry) => (
                  <TableRow key={entry.id} className={stackTable.row}>
                    <TableCell data-label="Action" className={stackTable.cell}>
                      {entry.action}
                    </TableCell>
                    <TableCell data-label="Actor" className={stackTable.cell}>
                      {entry.actor_display_name || "(system)"}
                    </TableCell>
                    <TableCell data-label="Target" className={stackTable.cell}>
                      {entry.target_display || entry.target_type || "-"}
                    </TableCell>
                    <TableCell
                      data-label="Timestamp"
                      className={`${stackTable.cell} whitespace-nowrap`}
                    >
                      {format(new Date(entry.created_at), "MMM d HH:mm")}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted">
                    No entries match filters
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>

        {auditLog.has_more && (
          <div className="mt-4 flex justify-center">
            <Button size="sm" onClick={() => setCursor(auditLog.next_cursor)}>
              Load more
              <ChevronRight className="size-4" aria-hidden="true" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
