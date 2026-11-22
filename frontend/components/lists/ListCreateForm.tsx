"use client";
/**
 * @file components/lists/ListCreateForm.tsx
 * @brief Create-list form body (custom or from template). Rendered inline on
 *        /app/lists/new and inside ListCreateModal for quick create.
 */
import * as React from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Option, Select } from "@/components/ui/Select";
import { Segmented } from "@/components/ui/page/Segmented";
import { Textarea } from "@/components/ui/Textarea";
import { MentionMenu } from "@/components/mentions/MentionMenu";
import { useMentionInput } from "@/components/mentions/useMentionInput";
import {
  useListCreate,
  useListTemplateClone,
  useListTemplates,
} from "@/hooks/useLists";
import { ColorInput, LIST_COLORS } from "./listFormFields";

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

export interface ListCreateFormProps {
  communityId: string;
  /** Create the list inside this group (visibility "subgroup"). */
  subgroupId?: string | null;
  /** Called after a successful create or clone. */
  onDone: () => void;
  onCancel: () => void;
}

/**
 * @brief New list form: mode switch, title, template picker, visibility, color.
 * @param props see ListCreateFormProps
 * @return form element with Cancel / Create actions
 */
export function ListCreateForm({
  communityId,
  subgroupId,
  onDone,
  onCancel,
}: ListCreateFormProps) {
  const create = useListCreate(communityId);
  const clone = useListTemplateClone(communityId);
  const templates = useListTemplates();
  const { register, handleSubmit, watch, control, formState, setValue } =
    useForm<FormData>({
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
  const descriptionValue = watch("description") || "";
  const descriptionRef = React.useRef<HTMLTextAreaElement | null>(null);
  const mention = useMentionInput(
    descriptionValue,
    (v) => setValue("description", v),
    descriptionRef,
  );

  const onSubmit = (d: FormData) => {
    if (d.mode === "template" && d.templateId) {
      const visibility = d.visibility === "members" ? "private" : d.visibility;
      clone.mutate(
        { id: d.templateId, options: { title: d.title, visibility } },
        { onSuccess: onDone },
      );
      return;
    }
    create.mutate(
      {
        title: d.title,
        description: d.description || null,
        ...(subgroupId
          ? { visibility: "subgroup" as const, subgroupId }
          : { visibility: d.visibility }),
        color: d.color,
      },
      { onSuccess: onDone },
    );
  };

  return (
    <form
      noValidate
      onSubmit={handleSubmit(onSubmit)}
      className="flex flex-col gap-4"
    >
      {/* Template clones cannot target a group, so groups start blank. */}
      {!subgroupId && (
        <Controller
          name="mode"
          control={control}
          render={({ field }) => (
            <Segmented
              label="Start from"
              value={field.value}
              onChange={field.onChange}
              options={[
                { value: "custom", label: "Custom" },
                { value: "template", label: "From template" },
              ]}
            />
          )}
        />
      )}
      {isTemplate && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-semibold">Template</legend>
          {templates.data?.templates.map((t) => (
            <label
              key={t.id}
              className="glass-item flex items-center gap-3 rounded-[20px] px-4 py-3 text-sm"
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
        <div className="relative">
          {mention.open && (
            <MentionMenu
              {...mention.menu}
              className="absolute bottom-full left-0 mb-2 z-50"
            />
          )}
          <Textarea
            ref={(el) => {
              descriptionRef.current = el;
              const { ref: hookRef } = register("description");
              if (typeof hookRef === "function") hookRef(el);
            }}
            label="Description"
            error={errors.description?.message}
            value={descriptionValue}
            onChange={mention.onTextChange}
            onKeyDown={mention.onKeyDown}
            {...mention.fieldProps}
          />
        </div>
      )}
      {subgroupId ? (
        <p className="text-sm text-muted">Visible to members of this group.</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-semibold">Visibility</span>
          <Controller
            name="visibility"
            control={control}
            render={({ field }) => (
              <Select
                label="Visibility"
                value={field.value}
                onValueChange={field.onChange}
              >
                <Option value="community">Community</Option>
                {!isTemplate && <Option value="members">Members only</Option>}
                <Option value="private">Private</Option>
              </Select>
            )}
          />
        </div>
      )}
      {!isTemplate && <ColorInput label="Color" {...register("color")} />}
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={create.isPending || clone.isPending}>
          Create
        </Button>
      </div>
    </form>
  );
}
