"use client";
/**
 * @file components/admin/AlertsTab.tsx
 * @brief Admin "Alerts" tab: Apprise targets for admin alerts and the
 *        member local-address opt-in. Target URLs are write-only.
 */
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Trash2 } from "lucide-react";
import { Button, IconButton, Input, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { SettingsRow } from "@/components/ui/SettingsRow";
import { useToasts } from "@/stores/toasts";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/adminApprise";
import { AdminLoading, AdminNotice } from "./AdminState";

const TARGETS = ["admin", "apprise", "targets"];
const SETTINGS = ["admin", "apprise", "settings"];

/** @brief Alerts tab: targets list, add form and local-address switch. */
export function AlertsTab() {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const confirm = useConfirmDialog((s) => s.confirm);
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");
  const targets = useQuery({ queryKey: TARGETS, queryFn: api.listTargets });
  const settings = useQuery({
    queryKey: SETTINGS,
    queryFn: api.getAppriseSettings,
  });
  const fail = (e: unknown) =>
    push({ variant: "danger", message: formatApiError(e) });
  const refresh = () => qc.invalidateQueries({ queryKey: TARGETS });

  const add = useMutation({
    mutationFn: () =>
      api.createTarget({
        apprise_url: url.trim(),
        ...(label.trim() ? { label: label.trim() } : {}),
      }),
    onSuccess: () => {
      setLabel("");
      setUrl("");
      return refresh();
    },
    onError: fail,
  });
  const remove = useMutation({
    mutationFn: api.deleteTarget,
    onSuccess: refresh,
    onError: fail,
  });
  const test = useMutation({
    mutationFn: api.testTarget,
    onSuccess: (r) =>
      push(
        r.status === "sent"
          ? { variant: "success", message: "Test alert sent" }
          : { variant: "danger", message: r.message || "Test failed" },
      ),
    onError: fail,
  });
  const toggle = useMutation({
    mutationFn: api.putAppriseSettings,
    onSuccess: (d) => qc.setQueryData(SETTINGS, d),
    onError: fail,
  });

  if (targets.isError || settings.isError)
    return (
      <AdminNotice tone="error">Failed to load alert settings</AdminNotice>
    );
  if (!targets.data || !settings.data) return <AdminLoading />;
  const onRemove = async (id: string, name: string) => {
    const ok = await confirm({
      title: "Remove alert target?",
      message: `${name} will stop receiving admin alerts.`,
      confirmLabel: "Remove",
      tone: "danger",
    });
    if (ok) remove.mutate(id);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) add.mutate();
  };

  return (
    <Panel className="flex flex-col gap-4">
      <div className="flex max-w-[880px] flex-col">
        <SettingsRow label="Targets">
          {targets.data.length === 0 ? (
            <p className="text-sm text-muted">No alert targets yet.</p>
          ) : (
            <ul className="space-y-2">
              {targets.data.map((t) => {
                const name = t.label || "Unnamed target";
                return (
                  <li key={t.id} className="flex items-center gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{name}</p>
                      {t.scheme && (
                        <p className="truncate text-xs text-muted">
                          {t.scheme}://…
                        </p>
                      )}
                    </div>
                    <IconButton
                      aria-label={`Test ${name}`}
                      disabled={test.isPending}
                      onClick={() => test.mutate(t.id)}
                    >
                      <Send className="size-4" />
                    </IconButton>
                    <IconButton
                      aria-label={`Remove ${name}`}
                      disabled={remove.isPending}
                      onClick={() => onRemove(t.id, name)}
                    >
                      <Trash2 className="size-4" />
                    </IconButton>
                  </li>
                );
              })}
            </ul>
          )}
        </SettingsRow>
        <SettingsRow
          label="Add target"
          description="Local addresses such as ntfy://192.168.1.10/topic are fine here."
        >
          <form onSubmit={submit} className="flex flex-col gap-3">
            <Input
              aria-label="Label"
              placeholder="Label (optional)"
              value={label}
              maxLength={100}
              onChange={(e) => setLabel(e.target.value)}
            />
            <Input
              aria-label="Apprise URL"
              type="password"
              autoComplete="off"
              placeholder="ntfy://host/topic"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <div>
              <Button type="submit" disabled={!url.trim() || add.isPending}>
                Add target
              </Button>
            </div>
          </form>
        </SettingsRow>
        <SettingsRow
          label="Let members use local addresses"
          description="Off blocks member apps that point at your home network."
        >
          <Switch
            aria-label="Let members use local addresses"
            checked={settings.data.allow_local}
            disabled={toggle.isPending}
            onCheckedChange={(v) => toggle.mutate(v)}
          />
        </SettingsRow>
      </div>
    </Panel>
  );
}
