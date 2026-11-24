"use client";
/**
 * @file components/admin/AuditLogTab.tsx
 * @brief Audit log: search, action and date filters, paging, CSV export.
 */
import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { formatDistanceToNowStrict, format } from "date-fns";
import { Button, Option, Select } from "@/components/ui";
import { Panel, SearchField, Toolbar } from "@/components/ui/page";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/shadcn/table";
import { formatApiError } from "@/lib/api/errors";
import {
  exportAuditCsv,
  listAudit,
  type AuditFilters,
} from "@/lib/api/auditLog";
import { useToasts } from "@/stores/toasts";
import { AdminLoading, AdminNotice, stackTable } from "./AdminState";

/**
 * @brief Turn an event code into a label, e.g. "invite.created" -> "Invite created".
 * @param code raw action code
 * @return sentence-case label
 */
const actionLabel = (code: string) => {
  const words = code.replace(/[._]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
};

const ANY = "any";
/** Action prefixes the backend writes, for the filter. */
const AREAS = [
  "admin.",
  "email.",
  "apprise.",
  "2fa.",
  "passkey.",
  "oauth.",
  "sso.",
  "signins.",
  "audit.",
  "data_export.",
];
const DATE_CLS =
  "h-11 rounded-full border border-[color-mix(in_srgb,var(--nx-ink)_14%,transparent)] bg-transparent px-4";

/**
 * @brief Audit log viewer: filter toolbar above a full-width table.
 * @return tab content
 */
export function AuditLogTab() {
  const push = useToasts((s) => s.push);
  const [f, setF] = useState<AuditFilters>({
    q: "",
    action: "",
    since: "",
    until: "",
  });
  const [busy, setBusy] = useState(false);
  const log = useInfiniteQuery({
    queryKey: ["admin", "audit-log", f],
    queryFn: ({ pageParam }) => listAudit(f, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_cursor,
  });
  const rows = log.data?.pages.flatMap((p) => p.items) ?? [];
  const filtered = !!(f.q || f.action || f.since || f.until);

  const download = async () => {
    setBusy(true);
    try {
      const text = await exportAuditCsv(f);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
      a.download = "audit.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      push({ variant: "danger", message: formatApiError(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <Toolbar className="mb-0">
        <SearchField
          label="Search audit log"
          placeholder="Action, person or IP"
          value={f.q}
          onChange={(q) => setF((s) => ({ ...s, q }))}
          debounceMs={300}
        />
        <Select
          label="Area"
          value={f.action || ANY}
          onValueChange={(v) =>
            setF((s) => ({ ...s, action: v === ANY ? "" : v }))
          }
        >
          <Option value={ANY}>All areas</Option>
          {AREAS.map((a) => (
            <Option key={a} value={a}>
              {actionLabel(a)}
            </Option>
          ))}
        </Select>
        <label className="flex items-center gap-2 text-sm">
          From
          <input
            type="date"
            value={f.since}
            max={f.until || undefined}
            onChange={(e) => setF((s) => ({ ...s, since: e.target.value }))}
            className={DATE_CLS}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          To
          <input
            type="date"
            value={f.until}
            min={f.since || undefined}
            onChange={(e) => setF((s) => ({ ...s, until: e.target.value }))}
            className={DATE_CLS}
          />
        </label>
        {filtered && (
          <Button
            variant="glass"
            size="sm"
            onClick={() => setF({ q: "", action: "", since: "", until: "" })}
          >
            Clear filters
          </Button>
        )}
        <Button variant="glass" size="sm" onClick={download} loading={busy}>
          <Download className="size-4" aria-hidden="true" />
          Export CSV
        </Button>
      </Toolbar>

      {log.isLoading ? (
        <AdminLoading />
      ) : log.error ? (
        <AdminNotice tone="error">Failed to load audit log</AdminNotice>
      ) : rows.length === 0 ? (
        <AdminNotice>
          {filtered ? "No entries match filters" : "No audit log entries"}
        </AdminNotice>
      ) : (
        <Panel as="div">
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
              {rows.map((entry) => (
                <TableRow key={entry.id} className={stackTable.row}>
                  <TableCell data-label="Action" className={stackTable.cell}>
                    {actionLabel(entry.action)}
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
                    <time
                      dateTime={new Date(entry.created_at).toISOString()}
                      title={format(new Date(entry.created_at), "PPpp")}
                    >
                      {formatDistanceToNowStrict(new Date(entry.created_at), {
                        addSuffix: true,
                      })}
                    </time>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
      )}
      {log.hasNextPage && (
        <div className="flex justify-center">
          <Button
            size="sm"
            onClick={() => log.fetchNextPage()}
            loading={log.isFetchingNextPage}
          >
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
