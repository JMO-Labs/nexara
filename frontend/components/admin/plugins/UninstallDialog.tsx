"use client";
/**
 * @file components/admin/plugins/UninstallDialog.tsx
 * @brief Confirm uninstall; optionally also delete the plugin's content.
 */
import { useState } from "react";
import { Button, Checkbox, Modal } from "@/components/ui";

/**
 * @brief Uninstall confirmation.
 * @param name plugin display name
 * @param onConfirm called with deleteContent (false unless ticked)
 * @return modal
 */
export function UninstallDialog({
  open,
  name,
  pending,
  onClose,
  onConfirm,
}: {
  open: boolean;
  name: string;
  pending?: boolean;
  onClose: () => void;
  onConfirm: (deleteContent: boolean) => void;
}) {
  const [del, setDel] = useState(false);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Uninstall ${name}?`}
      description="The plugin stops receiving events and its bot is removed."
    >
      <label className="flex items-center gap-2 text-sm">
        <Checkbox checked={del} onCheckedChange={(c) => setDel(c === true)} />
        Also delete all its posts and comments
      </label>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="destructive"
          loading={pending}
          onClick={() => onConfirm(del)}
        >
          Uninstall
        </Button>
      </div>
    </Modal>
  );
}
