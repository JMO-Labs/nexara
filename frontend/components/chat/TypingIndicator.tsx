'use client';
/**
 * @file components/chat/TypingIndicator.tsx
 * @brief Subtle "X is typing…" line shown above the composer.
 */
import Typography from '@mui/joy/Typography';

export interface TypingIndicatorProps {
  count: number;
}

export function TypingIndicator({ count }: TypingIndicatorProps) {
  if (count <= 0) return null;
  const text =
    count === 1 ? 'Someone is typing…' : `${count} people are typing…`;
  return (
    <Typography
      level="body-xs"
      textColor="text.tertiary"
      sx={{ px: 2, py: 0.5, fontStyle: 'italic' }}
    >
      {text}
    </Typography>
  );
}
