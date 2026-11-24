"use client";
/**
 * @file components/admin/AgeGroupsTab.tsx
 * @brief Admin "Age groups" tab: pending member suggestions (approve or
 *        reject) and the adult-approval setting.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X } from "lucide-react";
import { IconButton, Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { SettingsRow } from "@/components/ui/SettingsRow";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/ageGroups";
import { AdminLoading, AdminNotice } from "./AdminState";

const PENDING = ["admin", "age-groups", "pending"];
const SETTINGS = ["admin", "age-groups", "settings"];

/** @brief Age groups tab. */
export function AgeGroupsTab() {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const list = useQuery({ queryKey: PENDING, queryFn: api.listSuggestions });
  const settings = useQuery({
    queryKey: SETTINGS,
    queryFn: api.getAgeSettings,
  });
  const fail = (e: unknown) =>
    push({ variant: "danger", message: formatApiError(e) });
  const decide = useMutation({
    mutationFn: (v: { id: string; approve: boolean }) =>
      api.decideSuggestion(v.id, v.approve),
    onSuccess: (_d, v) => {
      qc.setQueryData<api.AgeSuggestion[]>(PENDING, (rows) =>
        (rows ?? []).filter((r) => r.id !== v.id),
      );
    },
    onError: fail,
  });
  const toggle = useMutation({
    mutationFn: api.putAgeSettings,
    onSuccess: (d) => qc.setQueryData(SETTINGS, d),
    onError: fail,
  });

  if (list.isError || settings.isError)
    return (
      <AdminNotice tone="error">Failed to load age group settings</AdminNotice>
    );
  if (!list.data || !settings.data) return <AdminLoading />;

  return (
    <Panel className="flex max-w-[880px] flex-col">
      <SettingsRow
        label="Adult changes need approval"
        description="When on, members can't move a profile to Adult without an admin approving it."
      >
        <Switch
          aria-label="Adult changes need approval"
          checked={settings.data.adult_requires_approval}
          disabled={toggle.isPending}
          onCheckedChange={(v) => toggle.mutate(v)}
        />
      </SettingsRow>
      <SettingsRow label="Suggestions" description="From other members.">
        {list.data.length === 0 ? (
          <p className="text-sm text-muted">No pending suggestions.</p>
        ) : (
          <ul className="space-y-2">
            {list.data.map((s) => {
              const label = (
                api.AGE_LABEL[s.age_group as api.AgeGroup] ?? s.age_group
              ).split(" (")[0];
              const who = s.subject_name || "member";
              return (
                <li key={s.id} className="flex items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">
                      {who} {"\u2192"} {label}
                    </p>
                    {s.suggested_by_name && (
                      <p className="text-xs text-muted">
                        Suggested by {s.suggested_by_name}
                      </p>
                    )}
                    {s.note && (
                      <p className="break-words text-xs text-muted">{s.note}</p>
                    )}
                  </div>
                  <IconButton
                    aria-label={`Approve ${label} for ${who}`}
                    disabled={decide.isPending}
                    onClick={() => decide.mutate({ id: s.id, approve: true })}
                  >
                    <Check className="size-4" aria-hidden="true" />
                  </IconButton>
                  <IconButton
                    aria-label={`Reject ${label} for ${who}`}
                    disabled={decide.isPending}
                    onClick={() => decide.mutate({ id: s.id, approve: false })}
                  >
                    <X className="size-4" aria-hidden="true" />
                  </IconButton>
                </li>
              );
            })}
          </ul>
        )}
      </SettingsRow>
    </Panel>
  );
}
