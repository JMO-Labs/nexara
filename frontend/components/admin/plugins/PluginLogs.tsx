"use client";
/**
 * @file components/admin/plugins/PluginLogs.tsx
 * @brief Last output lines of a host-run plugin, with a refresh button.
 */
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui";
import { formatApiError } from "@/lib/api/errors";
import { getPluginLogs } from "@/lib/api/plugins";

/**
 * @brief Logs panel.
 * @param pluginId manifest id
 * @return section with a scrollable <pre>
 */
export function PluginLogs({ pluginId }: { pluginId: string }) {
  const q = useQuery({
    queryKey: ["admin", "plugins", pluginId, "logs"],
    queryFn: () => getPluginLogs(pluginId),
  });
  const lines = q.data?.lines ?? [];
  return (
    <section aria-labelledby="plugin-logs" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h3 id="plugin-logs" className="text-sm font-semibold">
          Log
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void q.refetch()}
          loading={q.isFetching}
        >
          <RefreshCw aria-hidden="true" className="size-4" />
          Refresh
        </Button>
      </div>
      {q.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {formatApiError(q.error)}
        </p>
      ) : (
        <pre
          tabIndex={0}
          aria-label="Plugin log"
          className="glass-item max-h-80 overflow-auto rounded-[12px] p-3 text-xs whitespace-pre-wrap break-all"
        >
          {q.isPending
            ? "Loading…"
            : lines.length
              ? lines.join("\n")
              : "No output yet."}
        </pre>
      )}
    </section>
  );
}
