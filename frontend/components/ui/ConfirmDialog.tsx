"use client";
/**
 * @file components/ui/ConfirmDialog.tsx
 * @brief Global confirm dialog backed by useConfirmDialog store.
 *        Mount once in Shell. Use `await confirm({ ... })`.
 * @return true if confirmed, false if cancelled or Escaped.
 */
import { cn } from "@/lib/utils";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { Modal } from "./Modal";
import { Button } from "./shadcn/button";

export function ConfirmDialog() {
  const s = useConfirmDialog();
  return (
    <Modal
      open={s.isOpen}
      onClose={s.close}
      title={s.title}
      description={s.message}
      size="sm"
      footer={
        <>
          <Button
            variant="outline"
            onClick={s.close}
            data-testid="confirm-dialog-cancel"
          >
            {s.cancelLabel}
          </Button>
          <Button
            variant={s.tone === "danger" ? "destructive" : "default"}
            className={cn(s.tone !== "danger" && "bg-accent text-white")}
            onClick={s.accept}
            data-testid="confirm-dialog-confirm"
          >
            {s.confirmLabel}
          </Button>
        </>
      }
    >
      {null}
    </Modal>
  );
}

export default ConfirmDialog;
