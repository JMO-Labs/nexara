"use client";
/**
 * @file components/admin/plugins/InstalledTab.tsx
 * @brief Admin "Installed" plugins list with install action.
 */
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, EmptyState } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { listPlugins } from "@/lib/api/plugins";
import { AdminLoading, AdminNotice } from "@/components/admin/AdminState";
import { InstallUrlDialog } from "./InstallUrlDialog";

export const PLUGINS_KEY = ["admin", "plugins"];

/** @brief Installed plugins list. */
export function InstalledTab() {
  const [installing, setInstalling] = useState(false);
  const q = useQuery({ queryKey: PLUGINS_KEY, queryFn: listPlugins });
  if (q.isError)
    return <AdminNotice tone="error">Failed to load plugins</AdminNotice>;
  if (!q.data) return <AdminLoading />;
  return (
    <Panel className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setInstalling(true)}>Install plugin</Button>
      </div>
      {q.data.length === 0 ? (
        <EmptyState title="No plugins installed" />
      ) : (
        <ul className="flex flex-col gap-2">
          {q.data.map((p) => (
            <li key={p.id}>
              <Link
                href={`/app/admin/plugins/${encodeURIComponent(p.plugin_id)}`}
                className="glass-item flex min-h-11 flex-wrap items-center gap-2 rounded-[20px] p-3 outline-none focus-visible:outline-2 focus-visible:outline-accent"
              >
                <span className="min-w-0 flex-1 truncate text-sm font-medium">
                  {p.name}
                </span>
                <span className="text-xs text-muted">v{p.version}</span>
                <Badge tone={p.enabled ? "leaf" : "neutral"}>
                  {p.enabled ? "Enabled" : "Disabled"}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <InstallUrlDialog
        key={String(installing)}
        open={installing}
        onClose={() => setInstalling(false)}
      />
    </Panel>
  );
}
