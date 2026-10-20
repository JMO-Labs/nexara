"use client";
/**
 * @file components/galleries/GalleryCreateModal.tsx
 * @brief Form modal to create a new gallery.
 */
import * as React from "react";
import {
  Modal,
  Input,
  Textarea,
  Button,
  ScopeSelect,
  type ScopeValue,
} from "@/components/ui";
import { useCreateGallery } from "@/hooks/useGalleries";
import { useCalendars } from "@/hooks/useCalendars";

export interface GalleryCreateModalProps {
  open: boolean;
  onClose: () => void;
  defaultSubgroupId?: string | null;
}

/**
 * @brief Modal form for creating a gallery.
 * @param props see GalleryCreateModalProps
 * @return modal element
 */
export function GalleryCreateModal({
  open,
  onClose,
  defaultSubgroupId,
}: GalleryCreateModalProps) {
  const create = useCreateGallery();
  const { data: calendars } = useCalendars();
  const initialScope = (): ScopeValue => ({
    visibility: defaultSubgroupId ? "subgroup" : "community",
    subgroup_id: defaultSubgroupId ?? null,
  });
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [scope, setScope] = React.useState<ScopeValue>(initialScope);
  const [error, setError] = React.useState<string | null>(null);

  const myGroups = React.useMemo(
    () =>
      (calendars ?? [])
        .filter((c) => c.kind === "subgroup" && c.subgroup_id)
        .map((c) => ({ id: c.subgroup_id as string, name: c.name })),
    [calendars],
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (scope.visibility === "subgroup" && !scope.subgroup_id) {
      setError("Choose a group to share with.");
      return;
    }
    setError(null);
    const payload: {
      title: string;
      description: string | null;
      visibility: "community" | "subgroup" | "private";
      subgroup_id?: string | null;
    } = {
      title,
      description: description || null,
      visibility: scope.visibility,
    };
    if (scope.visibility === "subgroup" && scope.subgroup_id) {
      payload.subgroup_id = scope.subgroup_id;
    }
    await create.mutateAsync(payload);
    setTitle("");
    setDescription("");
    setScope(initialScope());
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New gallery">
      <form className="flex flex-col gap-4" onSubmit={submit}>
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Textarea
          label="Description"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        {!defaultSubgroupId && (
          <ScopeSelect value={scope} onChange={setScope} subgroups={myGroups} />
        )}
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default GalleryCreateModal;
