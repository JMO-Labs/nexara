"use client";
/**
 * @file components/admin/PluginApiKeys.tsx
 * @brief List, generate and revoke plugin API keys.
 */
import { useState } from "react";
import { Button } from "@/components/ui";
import {
  useGeneratePluginApiKey,
  useGetPluginApiKeys,
  useRevokePluginApiKey,
} from "@/lib/api/plugins";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { AdminLoading, AdminNotice } from "./AdminState";

/**
 * @brief API keys panel.
 * @param pluginId plugin id
 * @return panel element
 */
export function PluginApiKeys({ pluginId }: { pluginId: string }) {
  const { data, isLoading, error } = useGetPluginApiKeys(pluginId);
  const generate = useGeneratePluginApiKey(pluginId);
  const revoke = useRevokePluginApiKey(pluginId);
  const confirm = useConfirmDialog((s) => s.confirm);
  const [fresh, setFresh] = useState<string | null>(null);

  const onRevoke = async (id: string) => {
    const ok = await confirm({
      title: "Revoke API key?",
      message: "The plugin stops authenticating with this key immediately.",
      confirmLabel: "Revoke",
      tone: "danger",
    });
    if (ok) revoke.mutate(id);
  };

  if (isLoading) return <AdminLoading />;
  if (error)
    return <AdminNotice tone="error">Failed to load API keys</AdminNotice>;

  return (
    <div className="flex flex-col gap-3">
      {fresh && (
        <div
          role="status"
          className="rounded-xl border border-ink/20 p-3 text-sm"
        >
          Copy this key now; it will not be shown again.
          <code className="mt-1 block break-all">{fresh}</code>
        </div>
      )}
      <ul className="flex flex-col gap-2">
        {(data ?? []).map((k) => (
          <li
            key={k.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ink/10 p-2"
          >
            <div className="min-w-0">
              <code className="break-all text-xs">{k.masked_key}</code>
              <p className="text-xs text-muted">
                Created {new Date(k.created_at).toLocaleDateString()}
                {k.revoked_at ? " · Revoked" : ""}
              </p>
            </div>
            {!k.revoked_at && (
              <Button
                size="sm"
                variant="destructive"
                aria-label={`Revoke key ending ${k.masked_key.slice(-4)}`}
                onClick={() => onRevoke(k.id)}
              >
                Revoke
              </Button>
            )}
          </li>
        ))}
        {data?.length === 0 && (
          <li className="text-sm text-muted">No API keys.</li>
        )}
      </ul>
      <Button
        className="self-start"
        loading={generate.isPending}
        onClick={() =>
          generate.mutate(undefined, { onSuccess: (r) => setFresh(r.key) })
        }
      >
        Generate key
      </Button>
    </div>
  );
}
