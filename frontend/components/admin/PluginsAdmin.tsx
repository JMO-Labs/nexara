"use client";
/**
 * @file components/admin/PluginsAdmin.tsx
 * @brief Installed plugins list with enable toggle, configure and uninstall.
 */
import { useState } from "react";
import Link from "next/link";
import { Button, Card, Switch } from "@/components/ui";
import {
  useGetPlugins,
  useTogglePlugin,
  useUninstallPlugin,
  type Plugin,
} from "@/lib/api/plugins";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { AdminLoading, AdminNotice } from "./AdminState";
import { PluginInstallDialog } from "./PluginInstallDialog";

function Row({ p }: { p: Plugin }) {
  const toggle = useTogglePlugin(p.id);
  const uninstall = useUninstallPlugin(p.id);
  const confirm = useConfirmDialog((s) => s.confirm);
  const onUninstall = async () => {
    const ok = await confirm({
      title: `Uninstall ${p.name}?`,
      message: "The plugin is disabled and removed from this community.",
      confirmLabel: "Uninstall",
      tone: "danger",
    });
    if (ok) uninstall.mutate();
  };
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink/10 p-3">
      <div className="min-w-0">
        <p className="font-semibold">
          {p.name}{" "}
          <span className="text-xs font-normal text-muted">v{p.version}</span>
        </p>
        <p className="text-sm text-muted">{p.description}</p>
      </div>
      <div className="flex items-center gap-2">
        <Switch
          aria-label={`${p.name} enabled`}
          checked={p.is_enabled}
          disabled={toggle.isPending}
          onCheckedChange={(v) => toggle.mutate(v)}
        />
        <Button asChild size="sm" variant="outline">
          <Link href={`/app/admin/plugins/${encodeURIComponent(p.id)}`}>
            Configure
          </Link>
        </Button>
        <Button
          size="sm"
          variant="destructive"
          loading={uninstall.isPending}
          onClick={onUninstall}
        >
          Uninstall
        </Button>
      </div>
    </li>
  );
}

/**
 * @brief Plugin browser.
 * @return list with install dialog
 */
export function PluginsAdmin() {
  const { data, isLoading, error } = useGetPlugins();
  const [open, setOpen] = useState(false);
  if (isLoading) return <AdminLoading />;
  if (error)
    return <AdminNotice tone="error">Failed to load plugins</AdminNotice>;
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Installed plugins</h2>
        <Button onClick={() => setOpen(true)}>Install plugin</Button>
      </div>
      <ul className="flex flex-col gap-2">
        {(data ?? []).map((p) => (
          <Row key={p.id} p={p} />
        ))}
        {data?.length === 0 && (
          <li className="text-sm text-muted">No plugins installed.</li>
        )}
      </ul>
      <PluginInstallDialog open={open} onClose={() => setOpen(false)} />
    </Card>
  );
}
