"use client";
/**
 * @file components/galleries/GalleryCreateModal.tsx
 * @brief Form modal to create a new gallery.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
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

export function GalleryCreateModal({
  open,
  onClose,
  defaultSubgroupId,
}: GalleryCreateModalProps) {
  const create = useCreateGallery();
  const { data: calendars } = useCalendars();
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [scope, setScope] = React.useState<ScopeValue>({
    visibility: defaultSubgroupId ? "subgroup" : "community",
    subgroup_id: defaultSubgroupId ?? null,
  });

  const myGroups = React.useMemo(
    () =>
      (calendars ?? [])
        .filter((c) => c.kind === "subgroup" && c.subgroup_id)
        .map((c) => ({ id: c.subgroup_id as string, name: c.name })),
    [calendars],
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
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
    setScope({
      visibility: defaultSubgroupId ? "subgroup" : "community",
      subgroup_id: defaultSubgroupId ?? null,
    });
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New gallery">
      <Stack component="form" spacing={2} onSubmit={submit}>
        <FormControl required>
          <FormLabel>Title</FormLabel>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </FormControl>
        <FormControl>
          <FormLabel>Description</FormLabel>
          <Textarea
            minRows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </FormControl>
        {!defaultSubgroupId && (
          <ScopeSelect value={scope} onChange={setScope} subgroups={myGroups} />
        )}
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button
            variant="plain"
            color="neutral"
            type="button"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending}>
            Create
          </Button>
        </Stack>
      </Stack>
    </Modal>
  );
}

export default GalleryCreateModal;
