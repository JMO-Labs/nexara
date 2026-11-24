"use client";
/**
 * @file components/profile/SuggestAgeGroupDialog.tsx
 * @brief Dialog for suggesting another member's age group to admins.
 */
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button, Modal, Option, Select, Textarea } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import {
  AGE_GROUPS,
  AGE_LABEL,
  suggestAgeGroup,
  type AgeGroup,
} from "@/lib/api/ageGroups";

/**
 * @brief Suggest-age-group dialog.
 * @param open visibility
 * @param onClose close handler
 * @param subjectId member being suggested for
 * @param name member display name
 * @return modal
 */
export function SuggestAgeGroupDialog({
  open,
  onClose,
  subjectId,
  name,
}: {
  open: boolean;
  onClose: () => void;
  subjectId: string;
  name: string;
}) {
  const push = useToasts((s) => s.push);
  const [group, setGroup] = useState<AgeGroup>("adult");
  const [note, setNote] = useState("");
  const close = () => {
    setGroup("adult");
    setNote("");
    onClose();
  };
  const send = useMutation({
    mutationFn: () =>
      suggestAgeGroup({
        subject_id: subjectId,
        age_group: group,
        ...(note.trim() ? { note: note.trim() } : {}),
      }),
    onSuccess: () => {
      push({ variant: "success", message: "Suggestion sent to admins" });
      close();
    },
    onError: (e) => push({ variant: "danger", message: formatApiError(e) }),
  });
  return (
    <Modal
      open={open}
      onClose={close}
      title="Suggest age group"
      description={`Admins will review your suggestion for ${name}.`}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={close}>
            Cancel
          </Button>
          <Button loading={send.isPending} onClick={() => send.mutate()}>
            Send suggestion
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Select
          label="Age group"
          value={group}
          onValueChange={(v) => setGroup(v as AgeGroup)}
        >
          {AGE_GROUPS.map((g) => (
            <Option key={g} value={g}>
              {AGE_LABEL[g]}
            </Option>
          ))}
        </Select>
        <Textarea
          label="Note (optional)"
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>
    </Modal>
  );
}
