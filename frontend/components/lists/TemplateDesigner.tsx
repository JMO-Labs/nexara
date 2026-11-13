"use client";
/**
 * @file components/lists/TemplateDesigner.tsx
 * @brief Template designer: sortable field list, config panel, live preview.
 */
import { useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select, Option } from "@/components/ui/Select";
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import {
  reorder,
  validateTemplate,
  type TemplateDraft,
  type TemplateField,
} from "@/lib/lists/templateModel";
import { cn } from "@/lib/utils";
import { FieldConfigPanel } from "./FieldConfigPanel";
import { TemplatePreview } from "./TemplatePreview";

interface RowProps {
  field: TemplateField;
  selected: boolean;
  error?: string;
  onSelect: () => void;
  onDelete: () => void;
}

function Row({ field, selected, error, onSelect, onDelete }: RowProps) {
  const s = useSortable({ id: field.id });
  const style = {
    transform: CSS.Transform.toString(s.transform),
    transition: s.transition,
  };
  return (
    <li
      ref={s.setNodeRef}
      style={style}
      data-testid={`field-row-${field.id}`}
      className={cn(
        "flex items-center gap-2 rounded-xl border p-2 bg-bg",
        selected && "border-accent ring-2 ring-accent",
        s.isDragging && "z-10 opacity-80 shadow-lg",
      )}
    >
      <button
        type="button"
        aria-label={`Drag ${field.label || field.key}`}
        className="cursor-grab touch-none p-1"
        {...s.attributes}
        {...s.listeners}
      >
        <GripVertical className="size-4" />
      </button>
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className="flex-1 text-left text-sm"
      >
        {field.label || <em>Untitled</em>}{" "}
        <span className="text-xs opacity-60">({field.type_key})</span>
        {error && (
          <span role="alert" className="block text-xs text-destructive">
            {error}
          </span>
        )}
      </button>
      <IconButton
        aria-label={`Delete ${field.label || field.key}`}
        variant="ghost"
        size="sm"
        onClick={onDelete}
      >
        <Trash2 className="size-4" />
      </IconButton>
    </li>
  );
}

interface Props {
  initial: TemplateDraft;
  onSave: (draft: TemplateDraft) => void;
  saving?: boolean;
}

/**
 * @brief Designer for list templates.
 * @param props initial draft and save handler (wraps create/update mutation)
 * @return designer UI
 */
export function TemplateDesigner({ initial, onSave, saving }: Props) {
  const [name, setName] = useState(initial.name);
  const [fields, setFields] = useState(initial.fields);
  const [selId, setSelId] = useState<string | null>(
    initial.fields[0]?.id ?? null,
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ key: "", label: "", type_key: "text" });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const selected = fields.find((f) => f.id === selId);

  const patch = (id: string, p: Partial<TemplateField>) =>
    setFields((fs) => fs.map((f) => (f.id === id ? { ...f, ...p } : f)));
  const onDragEnd = (e: DragEndEvent) => {
    if (e.over)
      setFields((fs) => reorder(fs, String(e.active.id), String(e.over!.id)));
  };
  const remove = (id: string) => {
    setFields((fs) =>
      fs.filter((f) => f.id !== id).map((f, i) => ({ ...f, position: i })),
    );
    if (selId === id) setSelId(null);
  };
  const confirmAdd = () => {
    if (!draft.key.trim() || !draft.label.trim()) return;
    const id = `f_${Date.now().toString(36)}_${fields.length}`;
    setFields((fs) => [
      ...fs,
      { id, ...draft, key: draft.key.trim(), config: {}, position: fs.length },
    ]);
    setSelId(id);
    setAdding(false);
    setDraft({ key: "", label: "", type_key: "text" });
  };
  const save = () => {
    const errs = validateTemplate(name, fields);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    onSave({
      ...initial,
      name: name.trim(),
      fields: fields.map((f, i) => ({ ...f, position: i })),
    });
  };

  const typeSelect = (
    value: string,
    on: (v: string) => void,
    label: string,
  ) => (
    <Select label={label} value={value} onValueChange={on}>
      {fieldRegistry.keys().map((k) => (
        <Option key={k} value={k}>
          {fieldRegistry.get(k)!.label}
        </Option>
      ))}
    </Select>
  );

  return (
    <div className="flex flex-col gap-6">
      <Input
        label="Template name"
        value={name}
        error={errors.name}
        onChange={(e) => setName(e.target.value)}
      />
      <div className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={onDragEnd}
          >
            <SortableContext
              items={fields.map((f) => f.id)}
              strategy={verticalListSortingStrategy}
            >
              <ul className="flex flex-col gap-2" aria-label="Fields">
                {fields.map((f) => (
                  <Row
                    key={f.id}
                    field={f}
                    selected={f.id === selId}
                    error={errors[f.id]}
                    onSelect={() => setSelId(f.id)}
                    onDelete={() => remove(f.id)}
                  />
                ))}
              </ul>
            </SortableContext>
          </DndContext>
          <Button variant="outline" onClick={() => setAdding(true)}>
            <Plus className="size-4" /> Add field
          </Button>
        </div>
        {selected && (
          <FieldConfigPanel
            key={selected.id}
            field={selected}
            onChange={(p) => patch(selected.id, p)}
          />
        )}
      </div>
      <section aria-label="Preview">
        <h3 className="mb-2 font-semibold">Preview</h3>
        <TemplatePreview fields={fields} />
      </section>
      <Button onClick={save} loading={saving}>
        Save
      </Button>
      <Modal
        open={adding}
        onClose={() => setAdding(false)}
        title="Add field"
        footer={<Button onClick={confirmAdd}>Add</Button>}
      >
        <div className="flex flex-col gap-3">
          <Input
            label="Key"
            value={draft.key}
            onChange={(e) => setDraft({ ...draft, key: e.target.value })}
          />
          <Input
            label="Field label"
            value={draft.label}
            onChange={(e) => setDraft({ ...draft, label: e.target.value })}
          />
          {typeSelect(
            draft.type_key,
            (v) => setDraft({ ...draft, type_key: v }),
            "Field type",
          )}
        </div>
      </Modal>
    </div>
  );
}
