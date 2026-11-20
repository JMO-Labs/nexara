"use client";
/**
 * @file components/lists/ListEditForm.tsx
 * @brief Edit-list form body (title, description, expiry, color). Rendered
 *        inline on /app/lists/[id]/edit and inside ListEditModal.
 */
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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

export interface ListEditFormProps {
  list: List;
  communityId: string;
  /** Called after a successful save. */
  onDone: () => void;
  onCancel: () => void;
}

/**
 * @brief Edit list form with Cancel / Save actions.
 * @param props see ListEditFormProps
 * @return form element
 */
export function ListEditForm({
  list,
  communityId,
  onDone,
  onCancel,
}: ListEditFormProps) {
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
      { onSuccess: onDone },
    );

  return (
    <form
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
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={update.isPending}>
          Save
        </Button>
      </div>
    </form>
  );
}
