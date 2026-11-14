"use client";
/**
 * @file components/common/ReportButton.tsx
 * @brief Small "Report" button that opens ReportDialog.
 */
import * as React from "react";
import { Flag } from "lucide-react";
import { ReportDialog } from "@/components/moderation/ReportDialog";
import type { ReportTarget } from "@/lib/api/moderation";

export interface ReportButtonProps {
  targetType: ReportTarget;
  targetId: string;
  className?: string;
}

/**
 * @brief Report trigger + dialog.
 * @param targetType kind of content
 * @param targetId content id
 * @return button and dialog
 */
export function ReportButton({
  targetType,
  targetId,
  className,
}: ReportButtonProps) {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          className ??
          "inline-flex items-center gap-1 rounded font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        }
      >
        <Flag className="size-3" aria-hidden="true" />
        Report
      </button>
      <ReportDialog
        open={open}
        onClose={() => setOpen(false)}
        targetType={targetType}
        targetId={targetId}
      />
    </>
  );
}

export default ReportButton;
