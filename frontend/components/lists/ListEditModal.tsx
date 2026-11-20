"use client";
/**
 * @file components/lists/ListEditModal.tsx
 * @brief Quick-edit list modal (used from the list Settings tab); wraps
 *        ListEditForm.
 */
import { Modal } from "@/components/ui/Modal";
import type { List } from "@/lib/api/listTypes";
import { ListEditForm } from "./ListEditForm";

export interface ListEditModalProps {
  open: boolean;
  onClose: () => void;
  list: List;
  communityId: string;
}

/**
 * @brief Edit list modal.
 * @param props see ListEditModalProps
 * @return modal
 */
export function ListEditModal({
  open,
  onClose,
  list,
  communityId,
}: ListEditModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Edit list">
      <ListEditForm
        list={list}
        communityId={communityId}
        onDone={onClose}
        onCancel={onClose}
      />
    </Modal>
  );
}
