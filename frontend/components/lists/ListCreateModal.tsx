"use client";
/**
 * @file components/lists/ListCreateModal.tsx
 * @brief Quick-create list modal; wraps ListCreateForm.
 */
import { Modal } from "@/components/ui/Modal";
import { ListCreateForm } from "./ListCreateForm";

export interface ListCreateModalProps {
  open: boolean;
  onClose: () => void;
  communityId: string;
  /** Create the list inside this group (visibility "subgroup"). */
  subgroupId?: string | null;
}

/**
 * @brief New list modal.
 * @param props see ListCreateModalProps
 * @return modal
 */
export function ListCreateModal({
  open,
  onClose,
  communityId,
  subgroupId,
}: ListCreateModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="New list">
      <ListCreateForm
        communityId={communityId}
        subgroupId={subgroupId}
        onDone={onClose}
        onCancel={onClose}
      />
    </Modal>
  );
}
