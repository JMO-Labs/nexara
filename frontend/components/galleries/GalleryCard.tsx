'use client';
/**
 * @file components/galleries/GalleryCard.tsx
 * @brief Gallery tile with cover thumbnail + metadata.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Card, Chip } from '@/components/ui';
import { API_BASE } from '@/lib/auth/session';
import type { Gallery } from '@/lib/api/galleries';

export interface GalleryCardProps {
  gallery: Gallery;
  onSelect: (id: string) => void;
}

export function GalleryCard({ gallery, onSelect }: GalleryCardProps) {
  const cover = gallery.cover_media_id
    ? `${API_BASE}/api/v1/media/${gallery.cover_media_id}/thumbnail`
    : null;
  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onSelect(gallery.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(gallery.id);
        }
      }}
      sx={{ cursor: 'pointer', overflow: 'hidden', p: 0 }}
    >
      <Box
        sx={{
          aspectRatio: '4/3',
          background: cover ? `url(${cover}) center/cover` : 'var(--joy-palette-neutral-100)',
        }}
        aria-label={cover ? `${gallery.title} cover` : 'No cover image'}
      />
      <Stack spacing={0.5} sx={{ p: 2 }}>
        <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }} noWrap>
          {gallery.title}
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography level="body-xs" sx={{ color: 'text.tertiary' }}>
            {gallery.item_count} {gallery.item_count === 1 ? 'item' : 'items'}
          </Typography>
          {gallery.is_featured && <Chip size="sm" color="warning">Featured</Chip>}
        </Stack>
      </Stack>
    </Card>
  );
}

export default GalleryCard;
