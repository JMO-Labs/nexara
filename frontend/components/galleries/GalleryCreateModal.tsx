'use client';
/**
 * @file components/galleries/GalleryCreateModal.tsx
 * @brief Form modal to create a new gallery.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import { Modal, Input, Textarea, Select, Option, Button } from '@/components/ui';
import { useCreateGallery } from '@/hooks/useGalleries';

export interface GalleryCreateModalProps {
  open: boolean;
  onClose: () => void;
  defaultSubgroupId?: string | null;
}

export function GalleryCreateModal({ open, onClose, defaultSubgroupId }: GalleryCreateModalProps) {
  const create = useCreateGallery();
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [visibility, setVisibility] = React.useState<'community' | 'subgroup' | 'private'>(
    defaultSubgroupId ? 'subgroup' : 'community',
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create.mutateAsync({
      title,
      description: description || null,
      visibility,
      ...(defaultSubgroupId && { subgroup_id: defaultSubgroupId }),
    });
    setTitle('');
    setDescription('');
    setVisibility(defaultSubgroupId ? 'subgroup' : 'community');
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New gallery">
      <Stack component="form" spacing={2} onSubmit={submit}>
        <FormControl required>
          <FormLabel>Title</FormLabel>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
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
          <FormControl>
            <FormLabel>Visibility</FormLabel>
            <Select
              value={visibility}
              onChange={(_e, v) =>
                setVisibility((v as 'community' | 'subgroup' | 'private') ?? 'community')
              }
            >
              <Option value="community">Community</Option>
              <Option value="subgroup">Subgroup</Option>
              <Option value="private">Private</Option>
            </Select>
          </FormControl>
        )}
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button variant="plain" color="neutral" type="button" onClick={onClose}>
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
