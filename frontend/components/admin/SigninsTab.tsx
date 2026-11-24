"use client";
/**
 * @file components/admin/SigninsTab.tsx
 * @brief Admin sign-in log: search, success/method filters, paging, CSV export.
 */
import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { format } from "date-fns";
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
  exportSigninsCsv,
  listSignins,
  type SigninFilters,
} from "@/lib/api/signins";
import { useToasts } from "@/stores/toasts";
import { AdminLoading, AdminNotice, stackTable } from "./AdminState";

const METHODS = [
  "password",
  "totp",
  "recovery",
  "passkey",
  "magic_link",
  "sso",
];
const ANY = "any";

/**
 * @brief Sign-in log table with filters and export.
 * @return tab content
 */
export function SigninsTab() {
  const push = useToasts((s) => s.push);
  const [f, setF] = useState<SigninFilters>({
    q: "",
    success: "",
    method: "",
    since: "",
  });
  const [busy, setBusy] = useState(false);
  const log = useInfiniteQuery({
    queryKey: ["admin", "signins", f],
    queryFn: ({ pageParam }) => listSignins(f, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_cursor,
  });
  const rows = log.data?.pages.flatMap((p) => p.items) ?? [];

  const download = async () => {
    setBusy(true);
    try {
      const text = await exportSigninsCsv(f);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
      a.download = "signins.csv";
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
          label="Search sign-ins"
          placeholder="Email, IP or device"
          value={f.q}
          onChange={(q) => setF((s) => ({ ...s, q }))}
          debounceMs={300}
        />
        <Select
          label="Result"
          value={f.success || ANY}
          onValueChange={(v) =>
            setF((s) => ({
              ...s,
              success: v === ANY ? "" : (v as SigninFilters["success"]),
            }))
          }
        >
          <Option value={ANY}>All results</Option>
          <Option value="true">Succeeded</Option>
          <Option value="false">Failed</Option>
        </Select>
        <Select
          label="Method"
          value={f.method || ANY}
          onValueChange={(v) =>
            setF((s) => ({ ...s, method: v === ANY ? "" : v }))
          }
        >
          <Option value={ANY}>All methods</Option>
          {METHODS.map((m) => (
            <Option key={m} value={m}>
              {m.replaceAll("_", " ")}
            </Option>
          ))}
        </Select>
        <label className="flex items-center gap-2 text-sm">
          Since
          <input
            type="date"
            value={f.since}
            max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setF((s) => ({ ...s, since: e.target.value }))}
            className="h-11 rounded-full border border-[color-mix(in_srgb,var(--nx-ink)_14%,transparent)] bg-transparent px-4"
          />
        </label>
        <Button variant="glass" size="sm" onClick={download} loading={busy}>
          <Download className="size-4" aria-hidden="true" />
          Export CSV
        </Button>
      </Toolbar>

      {log.isLoading ? (
        <AdminLoading />
      ) : log.error ? (
        <AdminNotice tone="error">Failed to load sign-ins</AdminNotice>
      ) : rows.length === 0 ? (
        <AdminNotice>No sign-ins match</AdminNotice>
      ) : (
        <Panel as="div">
          <Table>
            <TableHeader className={stackTable.head}>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Who</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>IP</TableHead>
                <TableHead>Device</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id} className={stackTable.row}>
                  <TableCell
                    data-label="Time"
                    className={`${stackTable.cell} whitespace-nowrap`}
                  >
                    <time dateTime={r.time}>
                      {format(new Date(r.time), "PP p")}
                    </time>
                  </TableCell>
                  <TableCell data-label="Who" className={stackTable.cell}>
                    {r.user ?? r.email ?? "unknown"}
                  </TableCell>
                  <TableCell data-label="Method" className={stackTable.cell}>
                    {r.method.replaceAll("_", " ")}
                  </TableCell>
                  <TableCell data-label="Result" className={stackTable.cell}>
                    {r.success ? (
                      "Succeeded"
                    ) : (
                      <span className="font-medium text-destructive">
                        Failed
                        {r.reason ? ` (${r.reason.replaceAll("_", " ")})` : ""}
                      </span>
                    )}
                  </TableCell>
                  <TableCell data-label="IP" className={stackTable.cell}>
                    {r.ip ?? "-"}
                  </TableCell>
                  <TableCell data-label="Device" className={stackTable.cell}>
                    {r.device ?? "-"}
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
