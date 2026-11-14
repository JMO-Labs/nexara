"use client";
/**
 * @file components/lists/ListCreateModal.tsx
 * @brief Create a list from a template (clone) or as a custom list.
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
import {
  useListCreate,
  useListTemplateClone,
  useListTemplates,
} from "@/hooks/useLists";
import { ColorInput, LIST_COLORS, NativeSelect } from "./listFormFields";

const Schema = z
  .object({
    mode: z.enum(["custom", "template"]),
    templateId: z.string().nullish(),
    title: z.string().trim().min(1, "Title is required").max(200),
    description: z.string().max(2000).optional(),
    visibility: z.enum(["community", "members", "private"]),
    color: z.string(),
  })
  .refine((d) => d.mode === "custom" || Boolean(d.templateId), {
    message: "Choose a template",
    path: ["templateId"],
  });
type FormData = z.infer<typeof Schema>;

export interface ListCreateModalProps {
  open: boolean;
  onClose: () => void;
  communityId: string;
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
}: ListCreateModalProps) {
  const formId = useId();
  const create = useListCreate(communityId);
  const clone = useListTemplateClone(communityId);
  const templates = useListTemplates();
  const { register, handleSubmit, watch, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: {
      mode: "custom",
      title: "",
      description: "",
      visibility: "community",
      color: LIST_COLORS[0],
    },
  });
  const errors = formState.errors;
  const isTemplate = watch("mode") === "template";
  const done = { onSuccess: onClose };

  const onSubmit = (d: FormData) => {
    if (d.mode === "template" && d.templateId) {
      const visibility = d.visibility === "members" ? "private" : d.visibility;
      clone.mutate(
        { id: d.templateId, options: { title: d.title, visibility } },
        done,
      );
      return;
    }
    create.mutate(
      {
        title: d.title,
        description: d.description || null,
        visibility: d.visibility,
        color: d.color,
      },
      done,
    );
  };

  return (
    <Modal open={open} onClose={onClose} title="New list">
      <form
        id={formId}
        noValidate
        onSubmit={handleSubmit(onSubmit)}
        className="flex flex-col gap-4"
      >
        <fieldset className="flex gap-4">
          <legend className="sr-only">Start from</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" value="custom" {...register("mode")} />
            Custom
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" value="template" {...register("mode")} />
            From template
          </label>
        </fieldset>
        {isTemplate && (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-semibold">Template</legend>
            {templates.data?.templates.map((t) => (
              <label
                key={t.id}
                className="flex items-center gap-2 rounded-xl border border-current/15 p-2 text-sm"
              >
                <input type="radio" value={t.id} {...register("templateId")} />
                {t.name}
              </label>
            ))}
            {errors.templateId && (
              <p role="alert" className="text-sm text-destructive">
                {errors.templateId.message}
              </p>
            )}
          </fieldset>
        )}
        <Input
          label="Title"
          error={errors.title?.message}
          {...register("title")}
        />
        {!isTemplate && (
          <Textarea
            label="Description"
            error={errors.description?.message}
            {...register("description")}
          />
        )}
        <NativeSelect label="Visibility" {...register("visibility")}>
          <option value="community">Community</option>
          {!isTemplate && <option value="members">Members only</option>}
          <option value="private">Private</option>
        </NativeSelect>
        {!isTemplate && <ColorInput label="Color" {...register("color")} />}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending || clone.isPending}>
            Create
          </Button>
        </DialogFooter>
      </form>
    </Modal>
  );
}
