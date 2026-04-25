'use client';
/**
 * @file components/events/EventCreateModal.tsx
 * @brief Form modal for creating a new event.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import { Modal, Input, Textarea, Button, Select, Option } from '@/components/ui';
import { useCreateEvent } from '@/hooks/useEvents';

export interface EventCreateModalProps {
  open: boolean;
  onClose: () => void;
}

export function EventCreateModal({ open, onClose }: EventCreateModalProps) {
  const create = useCreateEvent();
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [location, setLocation] = React.useState('');
  const [startsAt, setStartsAt] = React.useState('');
  const [endsAt, setEndsAt] = React.useState('');
  const [allDay, setAllDay] = React.useState(false);
  const [visibility, setVisibility] = React.useState<'community' | 'subgroup' | 'private'>(
    'community',
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create.mutateAsync({
      title,
      description: description || null,
      location: location || null,
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      is_all_day: allDay,
      visibility,
    });
    setTitle('');
    setDescription('');
    setLocation('');
    setStartsAt('');
    setEndsAt('');
    setAllDay(false);
    setVisibility('community');
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="New event">
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
        <FormControl>
          <FormLabel>Location</FormLabel>
          <Input value={location} onChange={(e) => setLocation(e.target.value)} />
        </FormControl>
        <Stack direction="row" spacing={2}>
          <FormControl required sx={{ flex: 1 }}>
            <FormLabel>Starts</FormLabel>
            <Input
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              required
            />
          </FormControl>
          <FormControl required sx={{ flex: 1 }}>
            <FormLabel>Ends</FormLabel>
            <Input
              type="datetime-local"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
              required
            />
          </FormControl>
        </Stack>
        <FormControl>
          <Stack direction="row" spacing={1} alignItems="center">
            <input
              id="allday"
              type="checkbox"
              checked={allDay}
              onChange={(e) => setAllDay(e.target.checked)}
            />
            <FormLabel htmlFor="allday" sx={{ m: 0 }}>
              All day
            </FormLabel>
          </Stack>
        </FormControl>
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

export default EventCreateModal;
