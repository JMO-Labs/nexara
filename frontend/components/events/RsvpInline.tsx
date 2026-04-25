'use client';
/**
 * @file components/events/RsvpInline.tsx
 * @brief Inline RSVP toggle row using rsvp_labels (defaults to attending/maybe/declined).
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import { Chip } from '@/components/ui';
import { useRsvp } from '@/hooks/useEvents';

const DEFAULT_LABELS: Record<string, string> = {
  attending: 'Going',
  maybe: 'Maybe',
  declined: 'Decline',
};

export interface RsvpInlineProps {
  eventId: string;
  labels?: Record<string, string> | null;
  current?: string | null;
  counts?: Record<string, number>;
}

export function RsvpInline({ eventId, labels, current, counts }: RsvpInlineProps) {
  const merged = labels && Object.keys(labels).length ? labels : DEFAULT_LABELS;
  const rsvp = useRsvp(eventId);
  const onClick = (status: string) => {
    rsvp.mutate(current === status ? null : status);
  };
  return (
    <Stack direction="row" spacing={1} role="group" aria-label="RSVP">
      {Object.entries(merged).map(([status, label]) => {
        const active = current === status;
        const count = counts?.[status] ?? 0;
        return (
          <Chip
            key={status}
            variant={active ? 'solid' : 'outlined'}
            color={active ? 'primary' : 'neutral'}
            onClick={() => onClick(status)}
            disabled={rsvp.isPending}
          >
            {label}
            {count > 0 ? ` · ${count}` : ''}
          </Chip>
        );
      })}
    </Stack>
  );
}

export default RsvpInline;
