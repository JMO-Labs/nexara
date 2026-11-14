"use client";
/**
 * @file components/lists/ListMemberManageModal.tsx
 * @brief Manage members of a list: list, remove, add by user id + role.
 */
import { useId } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { UserMinus } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { DialogFooter } from "@/components/ui/shadcn/dialog";
import {
  useListMemberAdd,
  useListMemberRemove,
  useListMembers,
} from "@/hooks/useListActions";
import { NativeSelect } from "./listFormFields";

const Schema = z.object({
  userId: z.string().trim().uuid("Enter a valid user ID"),
  role: z.enum(["viewer", "editor"]),
});
type FormData = z.infer<typeof Schema>;

export interface ListMemberManageModalProps {
  open: boolean;
  onClose: () => void;
  listId: string;
}

/**
 * @brief Member management modal.
 * @param props see ListMemberManageModalProps
 * @return modal
 */
export function ListMemberManageModal({
  open,
  onClose,
  listId,
}: ListMemberManageModalProps) {
  const formId = useId();
  const members = useListMembers(listId);
  const add = useListMemberAdd(listId);
  const remove = useListMemberRemove(listId);
  const { register, handleSubmit, reset, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { userId: "", role: "viewer" },
  });

  const onSubmit = (d: FormData) => add.mutate(d, { onSuccess: () => reset() });

  return (
    <Modal open={open} onClose={onClose} title="Manage members">
      <ul aria-label="Members" className="flex flex-col gap-2">
        {members.data?.map((m) => (
          <li
            key={m.userId}
            className="flex items-center gap-2 rounded-xl border border-current/15 p-2 text-sm"
          >
            <span className="min-w-0 flex-1 truncate">{m.userId}</span>
            <Badge>{m.role}</Badge>
            {m.sharePersonal && (
              <Badge tone="accent">Shares personal info</Badge>
            )}
            <IconButton
              size="sm"
              variant="ghost"
              aria-label={`Remove ${m.userId}`}
              onClick={() => remove.mutate(m.userId)}
            >
              <UserMinus aria-hidden className="size-4" />
            </IconButton>
          </li>
        ))}
      </ul>
      <form
        id={formId}
        noValidate
        onSubmit={handleSubmit(onSubmit)}
        className="flex flex-col gap-3"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="flex-1">
            <Input
              label="User ID"
              error={formState.errors.userId?.message}
              {...register("userId")}
            />
          </div>
          <NativeSelect label="Role" {...register("role")}>
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
          </NativeSelect>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={add.isPending}>
            Add
          </Button>
        </DialogFooter>
      </form>
    </Modal>
  );
}
