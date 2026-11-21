"use client";
/**
 * @file components/admin/PluginsAdmin.tsx
 * @brief Installed plugins list with enable toggle, configure and uninstall.
 */
import { useState } from "react";
import Link from "next/link";
import { Puzzle } from "lucide-react";
import { Button, EmptyState, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
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
    if (ok) uninstall.mutate(undefined);
  };
  return (
    <li className="glass-item flex flex-wrap items-center justify-between gap-3 rounded-[20px] p-3">
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
        <Button asChild size="sm" variant="glass">
          <Link href={`/app/admin/plugins/${encodeURIComponent(p.id)}`}>
            Configure
          </Link>
        </Button>
        <Button
          size="sm"
          variant="glass"
          className="text-danger"
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
  const plugins = data ?? [];
  const installButton = (
    <Button size="sm" onClick={() => setOpen(true)}>
      Install plugin
    </Button>
  );
  return (
    <Panel
      title="Installed plugins"
      actions={plugins.length > 0 ? installButton : undefined}
    >
      {plugins.length === 0 ? (
        <EmptyState
          compact
          icon={Puzzle}
          title="No plugins yet"
          description="Install a plugin to add features to your community."
          action={installButton}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {plugins.map((p) => (
            <Row key={p.id} p={p} />
          ))}
        </ul>
      )}
      <PluginInstallDialog open={open} onClose={() => setOpen(false)} />
    </Panel>
  );
}
