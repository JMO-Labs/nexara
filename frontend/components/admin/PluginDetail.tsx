"use client";
/**
 * @file components/admin/PluginDetail.tsx
 * @brief Plugin detail: manifest, settings, API keys, lifecycle controls.
 */
import { useRouter } from "next/navigation";
import { Button, Card, Switch } from "@/components/ui";
import {
  useGetPlugins,
  useGetPluginManifest,
  useGetPluginSettings,
  useTogglePlugin,
  useUninstallPlugin,
} from "@/lib/api/plugins";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { AdminLoading, AdminNotice } from "./AdminState";
import { PluginApiKeys } from "./PluginApiKeys";
import { PluginPermissionList } from "./PluginPermissionList";
import { PluginSettingsForm } from "./PluginSettingsForm";

/**
 * @brief Detail view for one plugin.
 * @param id plugin id
 * @return detail element
 */
export function PluginDetail({ id }: { id: string }) {
  const router = useRouter();
  const manifest = useGetPluginManifest(id);
  const settings = useGetPluginSettings(id);
  const plugins = useGetPlugins();
  const toggle = useTogglePlugin(id);
  const uninstall = useUninstallPlugin(id);
  const confirm = useConfirmDialog((s) => s.confirm);

  if (manifest.isLoading || settings.isLoading || plugins.isLoading)
    return <AdminLoading />;
  const m = manifest.data;
  if (manifest.error || !m)
    return <AdminNotice tone="error">Failed to load plugin</AdminNotice>;
  const enabled = plugins.data?.find((p) => p.id === id)?.is_enabled ?? false;

  const onUninstall = async () => {
    const ok = await confirm({
      title: `Uninstall ${m.name}?`,
      message: "The plugin is disabled and removed from this community.",
      confirmLabel: "Uninstall",
      tone: "danger",
    });
    if (ok)
      uninstall.mutate(undefined, {
        onSuccess: () => router.push("/app/admin/plugins"),
      });
  };

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-2 p-4">
        <h2 className="text-lg font-semibold">
          {m.name}{" "}
          <span className="text-xs font-normal text-muted">v{m.version}</span>
        </h2>
        <p className="text-sm">{m.description}</p>
        <p className="text-xs text-muted">Author: {m.author}</p>
        <div className="flex items-center gap-3 pt-2">
          <Switch
            aria-label={`${m.name} enabled`}
            checked={enabled}
            disabled={toggle.isPending}
            onCheckedChange={(v) => toggle.mutate(v)}
          />
          <span className="text-sm">{enabled ? "Enabled" : "Disabled"}</span>
          <Button
            variant="destructive"
            size="sm"
            className="ml-auto"
            loading={uninstall.isPending}
            onClick={onUninstall}
          >
            Uninstall
          </Button>
        </div>
      </Card>
      <Card className="flex flex-col gap-2 p-4">
        <h3 className="text-lg font-semibold">Permissions</h3>
        <PluginPermissionList permissions={m.permissions} />
      </Card>
      <Card className="flex flex-col gap-3 p-4">
        <h3 className="text-lg font-semibold">Settings</h3>
        <PluginSettingsForm
          pluginId={id}
          schema={m.settings ?? {}}
          values={settings.data?.settings ?? {}}
        />
      </Card>
      <Card className="flex flex-col gap-3 p-4">
        <h3 className="text-lg font-semibold">API keys</h3>
        <PluginApiKeys pluginId={id} />
      </Card>
    </div>
  );
}
