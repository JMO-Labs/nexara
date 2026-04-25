'use client';
/**
 * @file components/media/MediaCard.tsx
 * @brief Thumbnail tile with filename + size.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Card } from '@/components/ui';
import { API_BASE } from '@/lib/auth/session';
import type { MediaItem } from '@/lib/api/media';

export interface MediaCardProps {
  media: MediaItem;
  onSelect?: (m: MediaItem) => void;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MediaCard({ media, onSelect }: MediaCardProps) {
  const thumb = `${API_BASE}/api/v1/media/${media.id}/thumbnail`;
  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(media)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect?.(media);
        }
      }}
      sx={{ cursor: onSelect ? 'pointer' : 'default', overflow: 'hidden', p: 0 }}
    >
      <Box
        sx={{
          aspectRatio: '1',
          background: `url(${thumb}) center/cover, var(--joy-palette-neutral-100)`,
        }}
        aria-label={media.alt_text ?? media.filename}
      />
      <Stack spacing={0.25} sx={{ p: 1.5 }}>
        <Typography level="body-sm" noWrap>
          {media.filename}
        </Typography>
        <Typography level="body-xs" sx={{ color: 'text.tertiary' }}>
          {fmtSize(media.size_bytes)}
        </Typography>
      </Stack>
    </Card>
  );
}

export default MediaCard;
