"use client";
/**
 * @file components/admin/RetentionPolicyRow.tsx
 * @brief Editable table row for one retention policy.
 */
import { useState } from "react";
import { Button, Switch } from "@/components/ui";
import { stackTable } from "./AdminState";
import {
  POLICY_META,
  policyLabel,
  validateDays,
  type RetentionPolicy,
  type RetentionUpdate,
} from "@/lib/retention-policies";

export interface RetentionPolicyRowProps {
  policy: RetentionPolicy;
  onSave: (key: string, body: RetentionUpdate) => void;
  saving: boolean;
}

/**
 * @brief One policy row with days input, toggles and a save button.
 * @param props policy, onSave, saving
 * @return table row
 */
export function RetentionPolicyRow({
  policy,
  onSave,
  saving,
}: RetentionPolicyRowProps) {
  const key = policy.policy_key;
  const meta = POLICY_META[key];
  const label = policyLabel(key);
  const [days, setDays] = useState(
    policy.retention_days === null ? "" : String(policy.retention_days),
  );
  const [enabled, setEnabled] = useState(policy.enabled);
  const [delMedia, setDelMedia] = useState(policy.delete_media_files);

  const parsed = days.trim() === "" ? null : Number(days);
  const error = validateDays(key, Number.isNaN(parsed) ? 0.5 : parsed);
  const dirty =
    enabled !== policy.enabled ||
    delMedia !== policy.delete_media_files ||
    parsed !== policy.retention_days;
  const hint = parsed === null && !error ? "Keep forever" : null;

  return (
    <tr className={stackTable.row}>
      <td className={stackTable.cell} data-label="Policy">
        <div>
          <div className="font-semibold">{label}</div>
          {meta?.dangerous && (
            <p role="alert" className="mt-1 text-xs font-semibold text-danger">
              Opt-in and destructive: when enabled this will permanently delete
              content older than the set age. Disabled by default.
            </p>
          )}
        </div>
      </td>
      <td className={stackTable.cell} data-label="Retention days">
        <div>
          <input
            type="number"
            inputMode="numeric"
            min={meta?.min}
            value={days}
            placeholder={meta?.allowForever ? "Forever" : undefined}
            aria-label={`${label} retention days`}
            aria-invalid={error ? true : undefined}
            onChange={(e) => setDays(e.target.value)}
            className="h-10 w-28 rounded-xl border border-ink/20 bg-surface px-2"
          />
          {hint && <div className="text-xs text-muted">{hint}</div>}
          {error && <div className="text-xs text-danger">{error}</div>}
        </div>
      </td>
      <td className={stackTable.cell} data-label="Enabled">
        <Switch
          checked={enabled}
          aria-label={`${label} enabled`}
          onCheckedChange={setEnabled}
        />
      </td>
      <td className={stackTable.cell} data-label="Delete media files">
        {meta?.media ? (
          <div>
            <Switch
              checked={delMedia}
              aria-label={`${label} delete media files`}
              onCheckedChange={setDelMedia}
            />
            {delMedia && (
              <div className="text-xs text-danger">
                Files are removed from storage and cannot be recovered.
              </div>
            )}
          </div>
        ) : (
          <span className="text-xs text-muted">n/a</span>
        )}
      </td>
      <td className={stackTable.cell} data-label="Actions">
        <Button
          type="button"
          aria-label={`Save ${label}`}
          disabled={!dirty || !!error || saving}
          onClick={() =>
            onSave(key, {
              enabled,
              retention_days: parsed,
              delete_media_files: meta?.media ? delMedia : false,
            })
          }
        >
          Save
        </Button>
      </td>
    </tr>
  );
}
