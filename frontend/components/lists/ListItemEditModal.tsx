"use client";
/**
 * @file components/lists/ListItemEditModal.tsx
 * @brief Create or edit a list item; inputs are generated from the list's
 *        fields using each type's registry Edit component.
 */
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { DialogFooter } from "@/components/ui/shadcn/dialog";
import { useListItemCreate } from "@/hooks/useLists";
import { useListItemUpdate } from "@/hooks/useListActions";
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import type { ListField } from "@/lib/lists/listFields";
import type { ListItem } from "@/lib/api/listTypes";

export interface ListItemEditModalProps {
  open: boolean;
  onClose: () => void;
  listId: string;
  fields: ListField[];
  /** Item to edit; omit to create a new one. */
  item?: ListItem;
  /** Position for a new item (defaults to 0). */
  nextPosition?: number;
}

const isEmpty = (v: unknown) =>
  v == null ||
  (typeof v === "string" && v.trim() === "") ||
  (Array.isArray(v) && v.length === 0);

/**
 * @brief Required-field validation.
 * @param fields list fields
 * @param values current values
 * @return error message per field key
 */
export function validateItem(
  fields: ListField[],
  values: Record<string, unknown>,
): Record<string, string> {
  return Object.fromEntries(
    fields
      .filter((f) => f.required && isEmpty(values[f.key]))
      .map((f) => [f.key, `${f.label} is required`]),
  );
}

/**
 * @brief Item form modal.
 * @param props see ListItemEditModalProps
 * @return modal
 */
export function ListItemEditModal({
  open,
  onClose,
  listId,
  fields,
  item,
  nextPosition = 0,
}: ListItemEditModalProps) {
  const formId = useId();
  const create = useListItemCreate(listId);
  const update = useListItemUpdate(listId);
  const [values, setValues] = useState<Record<string, unknown>>(
    () => item?.values ?? {},
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const pending = create.isPending || update.isPending;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const errs = validateItem(fields, values);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    const done = { onSuccess: onClose };
    if (item) update.mutate({ itemId: item.id, values }, done);
    else create.mutate({ position: nextPosition, values }, done);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={item ? "Edit item" : "New item"}
    >
      <form
        id={formId}
        onSubmit={onSubmit}
        noValidate
        className="flex flex-col gap-4"
      >
        {fields.map((f) => {
          const Edit = fieldRegistry.get(f.typeKey)?.Edit;
          if (!Edit) return null;
          const errId = `${formId}-${f.key}-err`;
          return (
            <div key={f.key} className="flex flex-col gap-1">
              <span className="text-sm font-semibold">
                {f.label}
                {f.required && <span aria-hidden> *</span>}
              </span>
              <Edit
                config={f.config}
                label={f.label}
                value={values[f.key]}
                onChange={(v) => setValues((s) => ({ ...s, [f.key]: v }))}
              />
              {errors[f.key] && (
                <p id={errId} role="alert" className="text-sm text-destructive">
                  {errors[f.key]}
                </p>
              )}
            </div>
          );
        })}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            Save
          </Button>
        </DialogFooter>
      </form>
    </Modal>
  );
}
