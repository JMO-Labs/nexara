"use client";
/**
 * @file components/memorials/MemorializeDialog.tsx
 * @brief Confirm dialog with an optional passed-on date. Used by the admin
 *        users table (memorialize an account) and the household page.
 */
import * as React from "react";
import { Button, Input, Modal } from "@/components/ui";

export interface MemorializeDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description: string;
  confirmLabel: string;
  /** Initial date, YYYY-MM-DD. */
  initial?: string | null;
  loading?: boolean;
  /** Called with the date, or null when left blank. */
  onConfirm: (passedOn: string | null) => void;
}

/**
 * @param props see MemorializeDialogProps
 * @return modal
 */
export function MemorializeDialog({
  open,
  onClose,
  title,
  description,
  confirmLabel,
  initial,
  loading,
  onConfirm,
}: MemorializeDialogProps) {
  const [date, setDate] = React.useState(initial ?? "");
  React.useEffect(() => {
    if (open) setDate(initial ?? "");
  }, [open, initial]);
  const today = new Date().toISOString().slice(0, 10);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={loading} onClick={() => onConfirm(date || null)}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <Input
        label="Passed on (optional)"
        type="date"
        max={today}
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />
    </Modal>
  );
}
