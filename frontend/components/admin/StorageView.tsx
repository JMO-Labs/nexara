"use client";
/**
 * @file components/admin/StorageView.tsx
 * @brief Storage analytics page body: summary, trend, breakdown, user table.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { getStorage, getStorageUsers } from "@/lib/api/adminStorage";
import { formatBytes } from "@/lib/formatBytes";
import { AdminLoading, AdminNotice } from "./AdminState";
import { StorageChart } from "./StorageChart";
import { StorageBreakdown } from "./StorageBreakdown";

type SortKey = "name" | "bytes" | "pct";

/** @brief Admin storage analytics view. */
function Th({
  k,
  label,
  sort,
  onSort,
}: {
  k: SortKey;
  label: string;
  sort: "ascending" | "descending" | "none";
  onSort: (k: SortKey) => void;
}) {
  return (
    <th scope="col" aria-sort={sort} className="p-2 text-left">
      <button
        type="button"
        onClick={() => onSort(k)}
        className="inline-flex min-h-11 items-center gap-1 font-medium text-muted hover:text-ink"
      >
        {label}
        {sort === "ascending" && (
          <ChevronUp className="size-4" aria-hidden="true" />
        )}
        {sort === "descending" && (
          <ChevronDown className="size-4" aria-hidden="true" />
        )}
        {sort === "none" && (
          <ChevronsUpDown className="size-4 opacity-50" aria-hidden="true" />
        )}
      </button>
    </th>
  );
}

export function StorageView() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "bytes",
    dir: "desc",
  });
  const overview = useQuery({
    queryKey: ["admin", "storage"],
    queryFn: getStorage,
    staleTime: 60_000,
  });
  const users = useQuery({
    queryKey: ["admin", "storage", "users", page],
    queryFn: () => getStorageUsers(page),
  });

  if (overview.isLoading) return <AdminLoading />;
  if (overview.error || !overview.data) {
    return <AdminNotice tone="error">Failed to load storage data</AdminNotice>;
  }
  const { current, snapshots } = overview.data;

  const rows = [...(users.data?.items ?? [])].sort((a, b) => {
    const m = sort.dir === "asc" ? 1 : -1;
    if (sort.key === "name")
      return m * a.display_name.localeCompare(b.display_name);
    if (sort.key === "pct")
      return m * (a.percent_of_total - b.percent_of_total);
    return m * (a.used_bytes - b.used_bytes);
  });
  const toggle = (key: SortKey) =>
    setSort((s) =>
      s.key === key
        ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "name" ? "asc" : "desc" },
    );
  const ariaSort = (key: SortKey) =>
    sort.key === key
      ? sort.dir === "asc"
        ? "ascending"
        : "descending"
      : "none";
  const pageSize = users.data?.page_size ?? 100;
  const pages = Math.max(1, Math.ceil((users.data?.total ?? 0) / pageSize));

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-item flex flex-col gap-1 rounded-[22px] p-4">
        <span className="text-sm text-muted">Total storage used</span>
        <span className="text-[32px] font-medium tracking-tight">
          {formatBytes(current.total_bytes)}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel as="div" title="Last 30 days">
          <StorageChart data={snapshots} />
        </Panel>
        <Panel as="div" title="By category">
          <StorageBreakdown categories={current.by_category} />
        </Panel>
      </div>
      <Panel as="div" title="Per-user storage" className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <Th
                k="name"
                label="Name"
                sort={ariaSort("name")}
                onSort={toggle}
              />
              <Th
                k="bytes"
                label="Used"
                sort={ariaSort("bytes")}
                onSort={toggle}
              />
              <Th
                k="pct"
                label="% of total"
                sort={ariaSort("pct")}
                onSort={toggle}
              />
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/5">
            {rows.map((u) => (
              <tr key={u.user_id}>
                <td className="p-2">{u.display_name}</td>
                <td className="p-2">{formatBytes(u.used_bytes)}</td>
                <td className="p-2">{u.percent_of_total.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {pages > 1 && (
          <nav aria-label="Pagination" className="mt-3 flex items-center gap-3">
            <Button
              variant="glass"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <span>
              Page {page} of {pages}
            </span>
            <Button
              variant="glass"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </nav>
        )}
      </Panel>
    </div>
  );
}
