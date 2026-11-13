"use client";
/**
 * @file components/moderation/ModerationQueue.tsx
 * @brief Admin table of pending reports with expand, per-row action and
 *        batch actions.
 */
import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button, Checkbox, Option, Select, Skeleton } from "@/components/ui";
import { useReportAction, useReports } from "@/hooks/useModeration";
import type { ReportActionType } from "@/lib/api/moderation";

const ACTIONS: { value: ReportActionType; label: string }[] = [
  { value: "dismiss", label: "Dismiss" },
  { value: "warn_user", label: "Warn" },
  { value: "hide_content", label: "Hide" },
  { value: "delete_content", label: "Delete" },
  { value: "ban_user", label: "Ban" },
];

/** @brief Moderation queue (admin). @return table element */
export function ModerationQueue() {
  const { data, isLoading, isError } = useReports();
  const act = useReportAction();
  const [open, setOpen] = React.useState<string | null>(null);
  const [sel, setSel] = React.useState<Set<string>>(new Set());
  const [notes, setNotes] = React.useState<Record<string, string>>({});
  const [batch, setBatch] = React.useState<ReportActionType>("dismiss");

  if (isLoading) return <Skeleton height={120} />;
  if (isError || !data) return <p role="alert">Couldn&apos;t load reports.</p>;
  const items = data.items;
  if (items.length === 0)
    return <p className="text-sm text-muted">No pending reports.</p>;

  const toggle = (id: string) =>
    setSel((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const applyBatch = async (action: ReportActionType) => {
    await Promise.all(
      [...sel].map((id) => act.mutateAsync({ id, action, note: notes[id] })),
    );
    setSel(new Set());
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm">{sel.size} selected</span>
        <div className="w-40">
          <Select
            label="Batch action"
            value={batch}
            onValueChange={(v) => setBatch(v as ReportActionType)}
          >
            {ACTIONS.map((a) => (
              <Option key={a.value} value={a.value}>
                {a.label}
              </Option>
            ))}
          </Select>
        </div>
        <Button
          size="sm"
          disabled={sel.size === 0}
          loading={act.isPending}
          onClick={() => applyBatch(batch)}
        >
          Apply to selected
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={sel.size === 0}
          onClick={() => applyBatch("dismiss")}
        >
          Dismiss selected
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-ink/15">
              <th className="w-8" />
              <th className="w-8" />
              <th>Date</th>
              <th>Content</th>
              <th>Reporter</th>
              <th>Reason</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <React.Fragment key={r.id}>
                <tr className="border-b border-ink/10 align-top">
                  <td>
                    <Checkbox
                      aria-label={`Select ${r.id}`}
                      checked={sel.has(r.id)}
                      onCheckedChange={() => toggle(r.id)}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      aria-label={`Expand report ${r.id}`}
                      aria-expanded={open === r.id}
                      onClick={() => setOpen(open === r.id ? null : r.id)}
                    >
                      {open === r.id ? (
                        <ChevronDown className="size-4" aria-hidden="true" />
                      ) : (
                        <ChevronRight className="size-4" aria-hidden="true" />
                      )}
                    </button>
                  </td>
                  <td>{new Date(r.created_at).toLocaleDateString()}</td>
                  <td>
                    {r.target_type}:{" "}
                    {(r.description ?? r.target_id).slice(0, 100)}
                  </td>
                  <td>{r.reporter_id.slice(0, 8)}</td>
                  <td>{r.reason}</td>
                  <td>
                    <div className="w-36">
                      <Select
                        label={`Action for ${r.id}`}
                        placeholder="Choose…"
                        onValueChange={(v) =>
                          act.mutateAsync({
                            id: r.id,
                            action: v as ReportActionType,
                            note: notes[r.id],
                          })
                        }
                      >
                        {ACTIONS.map((a) => (
                          <Option key={a.value} value={a.value}>
                            {a.label}
                          </Option>
                        ))}
                      </Select>
                    </div>
                  </td>
                </tr>
                {open === r.id ? (
                  <tr className="border-b border-ink/10 bg-surface">
                    <td colSpan={7} className="p-3">
                      <p>{r.description ?? "No details provided."}</p>
                      <p className="mt-1 text-xs text-muted">
                        Target {r.target_type} {r.target_id} · reporter{" "}
                        {r.reporter_id} · status {r.status}
                      </p>
                      <label className="mt-2 block text-xs font-semibold">
                        Admin notes
                        <textarea
                          className="mt-1 block w-full rounded border border-ink/20 bg-bg p-2 text-sm"
                          value={notes[r.id] ?? ""}
                          onChange={(e) =>
                            setNotes({ ...notes, [r.id]: e.target.value })
                          }
                        />
                      </label>
                    </td>
                  </tr>
                ) : null}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ModerationQueue;
