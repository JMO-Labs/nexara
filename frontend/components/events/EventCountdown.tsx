'use client';
/**
 * @file components/events/EventCountdown.tsx
 * @brief Live countdown widget: displays time until event with display font
 * (56px, weight 200) for numeric + uppercase units below (10px, tracking-wide).
 * Updates every 30s. Hairline dividers top + bottom.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import { useEventCountdown } from '@/hooks/useEventCountdown';
import type { EventItem } from '@/lib/api/events';

export function EventCountdown({ event }: { event: EventItem }) {
  const { days, hours, minutes } = useEventCountdown(event);

  const parts: Array<{ value: number; unit: string }> = [];
  if (days > 0) parts.push({ value: days, unit: 'days' });
  if (days > 0 || hours > 0) parts.push({ value: hours, unit: 'hours' });
  parts.push({ value: minutes, unit: 'min' });

  return (
    <Box
      sx={{
        borderTop: '1px solid',
        borderColor: 'divider',
        borderBottom: '1px solid',
        borderColor: 'divider',
        py: 2,
        px: 2,
        textAlign: 'center',
      }}
    >
      <Typography
        level="body-sm"
        sx={{
          mb: 1.5,
          fontWeight: 600,
          color: 'text.primary',
        }}
      >
        {event.title}
      </Typography>

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          gap: 1.5,
          alignItems: 'flex-end',
        }}
      >
        {parts.map((part, idx) => (
          <Box key={`${part.unit}-${idx}`} sx={{ textAlign: 'center' }}>
            <Typography
              sx={{
                fontFamily: 'var(--font-display)',
                fontSize: '56px',
                fontWeight: 200,
                lineHeight: 1,
                color: 'text.primary',
              }}
            >
              {part.value}
            </Typography>
            <Typography
              level="body-xs"
              sx={{
                fontSize: '10px',
                letterSpacing: '0.16em',
                textTransform: 'uppercase',
                color: 'text.tertiary',
                mt: 0.5,
              }}
            >
              {part.unit}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
