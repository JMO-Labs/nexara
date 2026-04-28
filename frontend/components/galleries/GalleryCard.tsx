'use client';
/**
 * @file components/galleries/GalleryCard.tsx
 * @brief Gallery tile with cover thumbnail + metadata + owner avatar.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Card, Chip, Avatar } from '@/components/ui';
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
      sx={{ cursor: 'pointer', overflow: 'hidden', p: 0, position: 'relative' }}
    >
      <Box
        sx={{
          aspectRatio: '4/3',
          background: cover ? `url(${cover}) center/cover` : 'var(--joy-palette-neutral-100)',
          position: 'relative',
        }}
        aria-label={cover ? `${gallery.title} cover` : 'No cover image'}
      >
        {/* Owner info with gradient backdrop */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 100%)',
            padding: '12px 8px 8px',
          }}
        >
          <Stack direction="row" spacing={0.75} alignItems="center">
            <Avatar
              data-testid="gallery-card-owner-avatar"
              sx={{ width: 18, height: 18, fontSize: '0.65rem' }}
              src={`${API_BASE}/api/v1/users/${gallery.owner_id}/avatar`}
              alt={gallery.owner_id}
            />
            <Typography
              level="body-xs"
              sx={{ color: 'white', fontWeight: 500, flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
            >
              {gallery.owner_id}
            </Typography>
          </Stack>
        </Box>
      </Box>
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
