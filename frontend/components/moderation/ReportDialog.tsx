"use client";
/**
 * @file components/moderation/ReportDialog.tsx
 * @brief Modal to report content: reason dropdown + optional details.
 */
import * as React from "react";
import { Button, Modal, Option, Select, Textarea } from "@/components/ui";
import { createReport } from "@/lib/api/moderation";
import type { ReportReason, ReportTarget } from "@/lib/api/moderation";
import { useToasts } from "@/stores/toasts";

export const REPORT_REASONS: { value: ReportReason; label: string }[] = [
  { value: "spam", label: "Spam" },
  { value: "harassment", label: "Harassment" },
  { value: "inappropriate", label: "Inappropriate" },
  { value: "misinformation", label: "Misinformation" },
  { value: "other", label: "Other" },
];

export interface ReportDialogProps {
  open: boolean;
  onClose: () => void;
  targetType: ReportTarget;
  targetId: string;
}

/**
 * @brief Report dialog.
 * @param open visibility
 * @param onClose close handler
 * @param targetType kind of content
 * @param targetId content id
 * @return modal element
 */
export function ReportDialog({
  open,
  onClose,
  targetType,
  targetId,
}: ReportDialogProps) {
  const push = useToasts((s) => s.push);
  const [reason, setReason] = React.useState("");
  const [details, setDetails] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await createReport({
        target_type: targetType,
        target_id: targetId,
        reason: reason as ReportReason,
        description: details.trim() || undefined,
      });
      push({ variant: "success", message: "Report submitted. Thank you." });
      setReason("");
      setDetails("");
      onClose();
    } catch {
      push({ variant: "danger", message: "Couldn't submit the report." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Report content"
      description="Tell moderators what is wrong with this content."
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!reason} loading={busy}>
            Submit report
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Select
          label="Reason"
          value={reason}
          onValueChange={setReason}
          placeholder="Select a reason"
        >
          {REPORT_REASONS.map((r) => (
            <Option key={r.value} value={r.value}>
              {r.label}
            </Option>
          ))}
        </Select>
        <Textarea
          label="Details (optional)"
          value={details}
          maxLength={2000}
          onChange={(e) => setDetails(e.target.value)}
        />
      </div>
    </Modal>
  );
}

export default ReportDialog;
