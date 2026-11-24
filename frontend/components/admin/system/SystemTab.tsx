"use client";
/**
 * @file components/admin/system/SystemTab.tsx
 * @brief Admin "System" tab: component health, disk and runtime. Polls 30s.
 */
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { Panel } from "@/components/ui/page";
import { getSystemHealth } from "@/lib/api/adminSystem";
import { AdminLoading, AdminNotice } from "../AdminState";
import { ComponentGrid } from "./ComponentGrid";
import { DiskPanel } from "./DiskPanel";
import { RuntimePanel } from "./RuntimePanel";

/**
 * @brief System health tab.
 * @return tab body
 */
export function SystemTab() {
  const q = useQuery({
    queryKey: ["admin", "system"],
    queryFn: getSystemHealth,
    refetchInterval: 30_000,
  });
  if (q.isError && !q.data)
    return <AdminNotice tone="error">Failed to load system health</AdminNotice>;
  if (!q.data) return <AdminLoading />;
  const { components, disk, runtime, grafana_url } = q.data;
  return (
    <Panel className="flex min-w-0 flex-col gap-4">
      <ComponentGrid components={components} />
      <div className="grid gap-3 md:grid-cols-2">
        <DiskPanel disk={disk} />
        <RuntimePanel runtime={runtime} />
      </div>
      {grafana_url && /^https?:\/\//i.test(grafana_url) && (
        <a
          href={grafana_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 self-start text-sm text-accent underline"
        >
          Open Grafana
          <span className="sr-only"> (opens in a new tab)</span>
          <ExternalLink aria-hidden="true" className="size-4" />
        </a>
      )}
    </Panel>
  );
}
