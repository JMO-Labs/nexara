"use client";
/**
 * @file components/admin/RetentionTab.tsx
 * @brief Retention policy list for the admin panel, one glass row per policy.
 */
import { useRetentionPolicies, useUpdateRetention } from "@/hooks/useRetention";
import { Panel } from "@/components/ui/page";
import { AdminLoading, AdminNotice } from "./AdminState";
import { RetentionPolicyRow } from "./RetentionPolicyRow";

/**
 * @brief Fetches and lists all retention policies inside one Panel.
 * @return panel with list, loading, or error state
 */
export function RetentionTab() {
  const { data, isLoading, error } = useRetentionPolicies();
  const update = useUpdateRetention();

  let body;
  if (isLoading) body = <AdminLoading />;
  else if (error)
    body = (
      <AdminNotice tone="error">Failed to load retention policies</AdminNotice>
    );
  else if (!data || data.length === 0)
    body = <AdminNotice>No retention policies configured</AdminNotice>;
  else
    body = (
      <ul className="flex flex-col gap-2">
        {data.map((p) => (
          <RetentionPolicyRow
            key={`${p.policy_key}:${p.updated_at}`}
            policy={p}
            saving={update.isPending}
            onSave={(key, body) => update.mutate({ key, body })}
          />
        ))}
      </ul>
    );

  return <Panel title="Retention policies">{body}</Panel>;
}
