"use client";
/**
 * @file components/moderation/ModerationQueue.tsx
 * @brief Admin table of pending reports with expand, per-row action and
 *        batch actions.
 */
import * as React from "react";
import { ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";
import {
  Button,
  Checkbox,
  EmptyState,
  IconButton,
  Option,
  Select,
} from "@/components/ui";
import { Toolbar } from "@/components/ui/page";
import { AdminNotice } from "@/components/admin/AdminState";
import { useReportAction, useReports } from "@/hooks/useModeration";
import type { ReportActionType } from "@/lib/api/moderation";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";

const ACTIONS: { value: ReportActionType; label: string }[] = [
  { value: "dismiss", label: "Dismiss" },
  { value: "warn_user", label: "Warn" },
  { value: "hide_content", label: "Hide" },
  { value: "delete_content", label: "Delete" },
  { value: "ban_user", label: "Ban" },
];

const DESTRUCTIVE = new Set<ReportActionType>(["delete_content", "ban_user"]);

/**
 * @brief Ask for confirmation when an action is destructive.
 * @param action chosen action
 * @param count number of reports affected
 * @return true when the action may proceed
 */
function confirmAction(action: ReportActionType, count: number) {
  if (!DESTRUCTIVE.has(action)) return Promise.resolve(true);
  const label = ACTIONS.find((a) => a.value === action)?.label ?? action;
  return useConfirmDialog.getState().confirm({
    title: `${label} for ${count} report${count === 1 ? "" : "s"}?`,
    message: "This cannot be undone.",
    confirmLabel: label,
    tone: "danger",
  });
}

/** @brief Moderation queue (admin). @return list of glass report rows */
export function ModerationQueue() {
  const { data, isLoading, isError } = useReports();
  const act = useReportAction();
  const push = useToasts((s) => s.push);
  const [open, setOpen] = React.useState<string | null>(null);
  const [sel, setSel] = React.useState<Set<string>>(new Set());
  const [notes, setNotes] = React.useState<Record<string, string>>({});
  const [batch, setBatch] = React.useState<ReportActionType>("dismiss");

  if (isLoading)
    return (
      <div
        role="status"
        aria-label="Loading reports"
        className="flex flex-col gap-2"
      >
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="glass-item h-16 rounded-[20px] motion-safe:animate-pulse"
          />
        ))}
      </div>
    );
  if (isError || !data)
    return <AdminNotice tone="error">Couldn&apos;t load reports.</AdminNotice>;
  const items = data.items;
  if (items.length === 0)
    return (
      <EmptyState
        compact
        icon={ShieldCheck}
        title="All clear"
        description="No reports are waiting for review."
      />
    );

  const toggle = (id: string) =>
    setSel((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const fail = () =>
    push({ variant: "danger", message: "Moderation action failed." });

  const applyBatch = async (action: ReportActionType) => {
    if (!(await confirmAction(action, sel.size))) return;
    try {
      await Promise.all(
        [...sel].map((id) => act.mutateAsync({ id, action, note: notes[id] })),
      );
      setSel(new Set());
    } catch {
      fail();
    }
  };

  const applyRow = async (id: string, action: ReportActionType) => {
    if (!(await confirmAction(action, 1))) return;
    try {
      await act.mutateAsync({ id, action, note: notes[id] });
    } catch {
      fail();
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <Toolbar className="mb-0">
        <span className="px-2 text-sm">{sel.size} selected</span>
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
          variant="glass"
          disabled={sel.size === 0}
          onClick={() => applyBatch("dismiss")}
        >
          Dismiss selected
        </Button>
      </Toolbar>
      <ul className="flex flex-col gap-2">
        {items.map((r) => (
          <li
            key={r.id}
            className="glass-item flex flex-col gap-2 rounded-[20px] p-3"
          >
            <div className="flex flex-wrap items-center gap-3">
              <Checkbox
                aria-label={`Select ${r.id}`}
                checked={sel.has(r.id)}
                onCheckedChange={() => toggle(r.id)}
              />
              <IconButton
                variant="glass"
                size="sm"
                aria-label={`Expand report ${r.id}`}
                aria-expanded={open === r.id}
                onClick={() => setOpen(open === r.id ? null : r.id)}
              >
                {open === r.id ? (
                  <ChevronDown className="size-4" aria-hidden="true" />
                ) : (
                  <ChevronRight className="size-4" aria-hidden="true" />
                )}
              </IconButton>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  {r.target_type}:{" "}
                  {(r.description ?? r.target_id).slice(0, 100)}
                </p>
                <p className="text-sm text-muted">
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                  {" · "}
                  <span>{r.reason}</span>
                  {" · "}
                  <span>Reporter {r.reporter_id.slice(0, 8)}</span>
                </p>
              </div>
              <div className="w-36">
                <Select
                  label={`Action for ${r.id}`}
                  placeholder="Choose…"
                  onValueChange={(v) =>
                    void applyRow(r.id, v as ReportActionType)
                  }
                >
                  {ACTIONS.map((a) => (
                    <Option key={a.value} value={a.value}>
                      {a.label}
                    </Option>
                  ))}
                </Select>
              </div>
            </div>
            {open === r.id ? (
              <div className="flex flex-col gap-2 px-1 pb-1">
                <p>{r.description ?? "No details provided."}</p>
                <p className="text-xs text-muted">
                  Target {r.target_type} {r.target_id} · reporter{" "}
                  {r.reporter_id} · status {r.status}
                </p>
                <label className="block text-xs font-semibold">
                  Admin notes
                  <textarea
                    className="glass-item mt-1 block w-full rounded-[20px] p-3 text-sm"
                    value={notes[r.id] ?? ""}
                    onChange={(e) =>
                      setNotes({ ...notes, [r.id]: e.target.value })
                    }
                  />
                </label>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ModerationQueue;
