"use client";
/**
 * @file components/admin/RetentionPolicyRow.tsx
 * @brief Editable glass row for one retention policy.
 */
import { useState } from "react";
import { TriangleAlert } from "lucide-react";
import { Button, Switch } from "@/components/ui";
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
 * @brief One policy row: stacked on phone; on md+ a fixed-column grid so
 *        every row aligns. Save appears only when the row is dirty.
 * @param props policy, onSave, saving
 * @return list item
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
    <li className="glass-item flex flex-col gap-3 rounded-[20px] p-3 md:grid md:grid-cols-[minmax(0,1fr)_7rem_8.5rem_9.5rem_5.5rem] md:items-center md:gap-3">
      <div className="min-w-0">
        <p className="font-medium">{label}</p>
        {meta?.dangerous && (
          <p
            role="alert"
            className="mt-1 flex items-start gap-1.5 text-[13px] text-danger"
          >
            <TriangleAlert
              className="mt-0.5 size-4 shrink-0"
              aria-hidden="true"
            />
            Permanently deletes content older than the set age. Off by default.
          </p>
        )}
        {meta?.media && delMedia && (
          <p className="mt-1 text-[13px] text-danger">
            Files are removed from storage and cannot be recovered.
          </p>
        )}
      </div>
      <div className="flex flex-col gap-1">
        <input
          type="number"
          inputMode="numeric"
          min={meta?.min}
          value={days}
          placeholder={meta?.allowForever ? "Forever" : undefined}
          aria-label={`${label} retention days`}
          aria-invalid={error ? true : undefined}
          onChange={(e) => setDays(e.target.value)}
          className="glass-item h-10 w-full rounded-full px-2 text-center text-ink"
        />
        {hint && <span className="text-xs text-muted">{hint}</span>}
        {error && <span className="text-xs text-danger">{error}</span>}
      </div>
      <span className="flex items-center gap-2 text-sm">
        <Switch
          checked={enabled}
          aria-label={`${label} enabled`}
          onCheckedChange={setEnabled}
        />
        Enabled
      </span>
      <div data-slot="delete-files" className="flex items-center gap-2 text-sm">
        {meta?.media && (
          <>
            <Switch
              checked={delMedia}
              aria-label={`${label} delete media files`}
              onCheckedChange={setDelMedia}
            />
            Delete files
          </>
        )}
      </div>
      <div data-slot="save">
        {dirty && (
          <Button
            type="button"
            size="sm"
            aria-label={`Save ${label}`}
            disabled={!!error || saving}
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
        )}
      </div>
    </li>
  );
}
