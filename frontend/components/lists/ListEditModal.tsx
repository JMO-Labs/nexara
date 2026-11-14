"use client";
/**
 * @file components/lists/ListEditModal.tsx
 * @brief Edit a list's title, description, expiry date and color.
 */
import { useId } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { DialogFooter } from "@/components/ui/shadcn/dialog";
import { Textarea } from "@/components/ui/Textarea";
import { useListUpdate } from "@/hooks/useLists";
import type { List } from "@/lib/api/listTypes";
import { ColorInput, LIST_COLORS } from "./listFormFields";

const Schema = z.object({
  title: z.string().trim().min(1, "Title is required").max(200),
  description: z.string().max(2000),
  expiresAt: z.string(),
  color: z.string(),
});
type FormData = z.infer<typeof Schema>;

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
  const formId = useId();
  const update = useListUpdate(communityId);
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: {
      title: list.title,
      description: list.description ?? "",
      expiresAt: list.expiresAt?.slice(0, 10) ?? "",
      color: list.color ?? LIST_COLORS[0],
    },
  });
  const errors = formState.errors;

  const onSubmit = (d: FormData) =>
    update.mutate(
      {
        id: list.id,
        data: {
          title: d.title,
          description: d.description || null,
          color: d.color,
          expiresAt: d.expiresAt || null,
        },
      },
      { onSuccess: onClose },
    );

  return (
    <Modal open={open} onClose={onClose} title="Edit list">
      <form
        id={formId}
        noValidate
        onSubmit={handleSubmit(onSubmit)}
        className="flex flex-col gap-4"
      >
        <Input
          label="Title"
          error={errors.title?.message}
          {...register("title")}
        />
        <Textarea
          label="Description"
          error={errors.description?.message}
          {...register("description")}
        />
        <Input type="date" label="Expires" {...register("expiresAt")} />
        <ColorInput label="Color" {...register("color")} />
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={update.isPending}>
            Save
          </Button>
        </DialogFooter>
      </form>
    </Modal>
  );
}
