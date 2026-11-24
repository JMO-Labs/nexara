"use client";
/**
 * @file components/settings/PluginPrefsTab.tsx
 * @brief Member preferences for each enabled plugin that declares any.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card } from "@/components/ui";
import { ManifestFieldsForm } from "@/components/plugins/ManifestFieldsForm";
import { usePluginUi } from "@/hooks/usePluginUi";
import {
  getPluginPrefs,
  putPluginPrefs,
  type PluginUi,
} from "@/lib/api/plugins";
import { useToasts } from "@/stores/toasts";

function PluginPrefs({ plugin }: { plugin: PluginUi }) {
  const qc = useQueryClient();
  const key = ["plugins", "prefs", plugin.plugin_id];
  const { data, isError, refetch } = useQuery({
    queryKey: key,
    queryFn: () => getPluginPrefs(plugin.plugin_id),
  });
  const save = useMutation({
    mutationFn: (v: Record<string, unknown>) =>
      putPluginPrefs(plugin.plugin_id, v),
    onSuccess: (v) => {
      qc.setQueryData(key, v);
      useToasts.getState().push({ variant: "success", message: "Saved" });
    },
    onError: (e: Error) =>
      useToasts.getState().push({ variant: "danger", message: e.message }),
  });
  return (
    <Card className="flex flex-col gap-3 p-4">
      <h2 className="text-base font-semibold">{plugin.name}</h2>
      {data ? (
        <ManifestFieldsForm
          fields={plugin.user_prefs}
          values={data}
          pending={save.isPending}
          onSubmit={(v) => save.mutate(v)}
        />
      ) : isError ? (
        <div role="alert" className="flex items-center gap-2 text-sm">
          <span>Could not load your preferences.</span>
          <Button size="sm" variant="ghost" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted">Loading…</p>
      )}
    </Card>
  );
}

/**
 * @brief Settings tab body.
 * @return one card per plugin with member prefs
 */
export function PluginPrefsTab() {
  const { data = [] } = usePluginUi();
  const withPrefs = data.filter((p) => Object.keys(p.user_prefs).length > 0);
  if (!withPrefs.length)
    return <p className="text-sm text-muted">No plugin preferences to set.</p>;
  return (
    <>
      {withPrefs.map((p) => (
        <PluginPrefs key={p.plugin_id} plugin={p} />
      ))}
    </>
  );
}
