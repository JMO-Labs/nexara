"use client";
/**
 * @file components/admin/plugins/PluginDetail.tsx
 * @brief Admin plugin detail: status, grants, enable switch, settings form
 *        and uninstall.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { SettingsRow } from "@/components/ui/SettingsRow";
import { ManifestFieldsForm } from "@/components/plugins/ManifestFieldsForm";
import { AdminLoading, AdminNotice } from "@/components/admin/AdminState";
import { useSession } from "@/stores/session";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/plugins";
import { PLUGINS_KEY } from "./InstalledTab";
import { CredentialsDialog } from "./CredentialsDialog";
import { UninstallDialog } from "./UninstallDialog";

const list = (items: string[]) => (items.length ? items.join(", ") : "None");

/**
 * @brief Plugin detail view.
 * @param pluginId manifest id from the route
 * @return detail panel
 */
export function PluginDetail({ pluginId }: { pluginId: string }) {
  const qc = useQueryClient();
  const router = useRouter();
  const push = useToasts((s) => s.push);
  const communityId = useSession((s) => s.user?.community_id);
  const [creds, setCreds] = useState<api.PluginCredentials | null>(null);
  const [removing, setRemoving] = useState(false);
  const fail = (e: unknown) =>
    push({ variant: "danger", message: formatApiError(e) });

  const plugins = useQuery({ queryKey: PLUGINS_KEY, queryFn: api.listPlugins });
  const settingsKey = ["admin", "plugins", pluginId, "settings"];
  const settings = useQuery({
    queryKey: settingsKey,
    queryFn: () => api.getPluginSettings(pluginId),
  });

  const patch = useMutation({
    mutationFn: (body: {
      enabled?: boolean;
      settings?: Record<string, unknown>;
    }) => api.setPluginCommunity(pluginId, communityId ?? "", body),
    onSuccess: async (r, body) => {
      if (r.credentials) setCreds(r.credentials);
      if (body.settings)
        push({ variant: "success", message: "Settings saved" });
      await qc.invalidateQueries({ queryKey: PLUGINS_KEY });
    },
    onError: fail,
  });
  const remove = useMutation({
    mutationFn: (del: boolean) => api.uninstallPlugin(pluginId, del),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: PLUGINS_KEY });
      router.push("/app/admin/plugins");
    },
    onError: fail,
  });

  if (plugins.isError || settings.isError)
    return <AdminNotice tone="error">Failed to load plugin</AdminNotice>;
  if (!plugins.data || !settings.data) return <AdminLoading />;
  const p = plugins.data.find((x) => x.plugin_id === pluginId);
  if (!p) return <AdminNotice tone="error">Plugin not found</AdminNotice>;
  const hasSettings = Object.keys(p.settings_schema).length > 0;

  return (
    <Panel className="flex max-w-[880px] flex-col gap-2">
      <h2 className="text-lg font-semibold">{p.name}</h2>
      <SettingsRow label="Status">
        <Badge tone={p.status === "active" ? "leaf" : "neutral"}>
          {p.status}
        </Badge>
      </SettingsRow>
      <SettingsRow label="Version">
        <span className="text-sm">v{p.version}</span>
      </SettingsRow>
      {p.tier && (
        <SettingsRow label="Tier">
          <span className="text-sm">{p.tier}</span>
        </SettingsRow>
      )}
      <SettingsRow label="Scopes">
        <span className="text-sm">{list(p.scopes)}</span>
      </SettingsRow>
      <SettingsRow label="Events">
        <span className="text-sm">{list(p.events)}</span>
      </SettingsRow>
      <SettingsRow label="Egress hosts">
        <span className="text-sm">{list(p.egress)}</span>
      </SettingsRow>
      <SettingsRow label="Enabled in this community">
        <Switch
          aria-label="Enabled in this community"
          checked={p.enabled}
          disabled={patch.isPending || !communityId}
          onCheckedChange={(enabled) => patch.mutate({ enabled })}
        />
      </SettingsRow>
      {hasSettings && (
        <SettingsRow label="Settings">
          <ManifestFieldsForm
            fields={p.settings_schema}
            values={settings.data}
            pending={patch.isPending}
            onSubmit={(s) => patch.mutate({ settings: s })}
          />
        </SettingsRow>
      )}
      <div className="pt-2">
        <Button variant="destructive" onClick={() => setRemoving(true)}>
          Uninstall
        </Button>
      </div>
      <CredentialsDialog credentials={creds} onClose={() => setCreds(null)} />
      <UninstallDialog
        key={String(removing)}
        open={removing}
        name={p.name}
        pending={remove.isPending}
        onClose={() => setRemoving(false)}
        onConfirm={(del) => remove.mutate(del)}
      />
    </Panel>
  );
}
