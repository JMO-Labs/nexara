'use client';
/**
 * @file components/galleries/GalleryUploadModal.tsx
 * @brief Two-step modal: gallery selector + uploader.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import { Modal, Input, Textarea, Select, Option, Button } from '@/components/ui';
import { GalleryUpload } from './GalleryUpload';
import { useGalleryList, useCreateGallery } from '@/hooks/useGalleries';

export interface GalleryUploadModalProps {
  open: boolean;
  onClose: () => void;
  subgroupId: string;
}

export function GalleryUploadModal({
  open,
  onClose,
  subgroupId,
}: GalleryUploadModalProps) {
  const create = useCreateGallery();
  const { data: galleriesData } = useGalleryList({ subgroup_id: subgroupId });

  const [step, setStep] = React.useState<'select' | 'upload'>('select');
  const [selectedGalleryId, setSelectedGalleryId] = React.useState<string | null>(null);
  const [showNewGalleryForm, setShowNewGalleryForm] = React.useState(false);
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');

  const galleries = galleriesData?.items ?? [];

  const handleCreateAndUpload = async () => {
    if (!title.trim()) return;
    try {
      const result = await create.mutateAsync({
        title,
        description: description || null,
        visibility: 'subgroup',
        subgroup_id: subgroupId,
      });
      setSelectedGalleryId(result.id);
      setTitle('');
      setDescription('');
      setShowNewGalleryForm(false);
      setStep('upload');
    } catch (err) {
      console.error('Failed to create gallery', err);
    }
  };

  const handleSelectExisting = (galleryId: string) => {
    setSelectedGalleryId(galleryId);
    setStep('upload');
  };

  const handleClose = () => {
    setStep('select');
    setSelectedGalleryId(null);
    setShowNewGalleryForm(false);
    setTitle('');
    setDescription('');
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={step === 'select' ? 'Upload media' : 'Upload media'}
    >
      {step === 'select' ? (
        <Stack spacing={2}>
          {!showNewGalleryForm ? (
            <>
              <FormControl>
                <FormLabel>Select a gallery</FormLabel>
                <Select
                  value={selectedGalleryId ?? ''}
                  onChange={(_e, v) => {
                    if (v === 'new') {
                      setShowNewGalleryForm(true);
                    } else if (v) {
                      handleSelectExisting(v as string);
                    }
                  }}
                  slotProps={{ listbox: { sx: { maxHeight: '300px' } } }}
                >
                  {galleries.map((g) => (
                    <Option key={g.id} value={g.id}>
                      {g.title}
                    </Option>
                  ))}
                  <Option value="new">+ Create new gallery</Option>
                </Select>
              </FormControl>
              <Stack direction="row" spacing={1} justifyContent="flex-end">
                <Button variant="plain" color="neutral" onClick={handleClose}>
                  Cancel
                </Button>
              </Stack>
            </>
          ) : (
            <>
              <FormControl required>
                <FormLabel>Gallery title</FormLabel>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="e.g. Summer 2026"
                />
              </FormControl>
              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea
                  minRows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                />
              </FormControl>
              <Stack direction="row" spacing={1} justifyContent="flex-end">
                <Button
                  variant="plain"
                  color="neutral"
                  onClick={() => setShowNewGalleryForm(false)}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  loading={create.isPending}
                  onClick={handleCreateAndUpload}
                  disabled={!title.trim()}
                >
                  Create & Upload
                </Button>
              </Stack>
            </>
          )}
        </Stack>
      ) : selectedGalleryId ? (
        <Stack spacing={2}>
          <GalleryUpload galleryId={selectedGalleryId} />
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button variant="plain" color="neutral" onClick={handleClose}>
              Done
            </Button>
          </Stack>
        </Stack>
      ) : null}
    </Modal>
  );
}

export default GalleryUploadModal;
