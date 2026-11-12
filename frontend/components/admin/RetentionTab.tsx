"use client";
/**
 * @file components/admin/RetentionTab.tsx
 * @brief Retention policy table for the admin panel.
 */
import { useRetentionPolicies, useUpdateRetention } from "@/hooks/useRetention";
import { AdminLoading, AdminNotice, stackTable } from "./AdminState";
import { RetentionPolicyRow } from "./RetentionPolicyRow";

const HEADS = ["Policy", "Retention days", "Enabled", "Delete media files", ""];

/**
 * @brief Fetches and lists all retention policies.
 * @return table, loading, or error state
 */
export function RetentionTab() {
  const { data, isLoading, error } = useRetentionPolicies();
  const update = useUpdateRetention();

  if (isLoading) return <AdminLoading />;
  if (error) {
    return (
      <AdminNotice tone="error">Failed to load retention policies</AdminNotice>
    );
  }
  if (!data || data.length === 0) {
    return <AdminNotice>No retention policies configured</AdminNotice>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className={stackTable.head}>
        <tr>
          {HEADS.map((h, i) => (
            <th key={i} scope="col" className="p-2">
              {h || <span className="sr-only">Actions</span>}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((p) => (
          <RetentionPolicyRow
            key={`${p.policy_key}:${p.updated_at}`}
            policy={p}
            saving={update.isPending}
            onSave={(key, body) => update.mutate({ key, body })}
          />
        ))}
      </tbody>
    </table>
  );
}
