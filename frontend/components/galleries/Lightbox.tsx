'use client';
/**
 * @file components/galleries/Lightbox.tsx
 * @brief Full-screen modal viewer for gallery items with arrow nav + Esc.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { IconButton } from '@/components/ui';
import {
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { API_BASE } from '@/lib/auth/session';
import type { GalleryItem } from '@/lib/api/galleries';

export interface LightboxProps {
  items: GalleryItem[];
  index: number;
  onClose: () => void;
  onIndexChange: (i: number) => void;
}

export function Lightbox({ items, index, onClose, onIndexChange }: LightboxProps) {
  const item = items[index];

  const next = React.useCallback(() => {
    if (index < items.length - 1) onIndexChange(index + 1);
  }, [index, items.length, onIndexChange]);
  const prev = React.useCallback(() => {
    if (index > 0) onIndexChange(index - 1);
  }, [index, onIndexChange]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowRight') next();
      else if (e.key === 'ArrowLeft') prev();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, next, prev]);

  if (!item) return null;
  const src = `${API_BASE}/api/v1/media/${item.media_id}/file`;

  return (
    <Box
      role="dialog"
      aria-modal="true"
      aria-label="Lightbox viewer"
      onClick={onClose}
      sx={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.85)',
        zIndex: 1500,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        sx={{ p: 2 }}
        onClick={(e) => e.stopPropagation()}
      >
        <Typography level="body-sm" sx={{ color: 'common.white' }}>
          {index + 1} / {items.length}
        </Typography>
        <IconButton tooltip="Close" shortcut="Esc" variant="plain" aria-label="Close" onClick={onClose}>
          <XMarkIcon width={24} height={24} color="white" />
        </IconButton>
      </Stack>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="center"
        sx={{ flex: 1, minHeight: 0, position: 'relative' }}
        onClick={(e) => e.stopPropagation()}
      >
        <IconButton
          tooltip="Previous"
          shortcut="←"
          aria-label="Previous"
          onClick={prev}
          disabled={index === 0}
          sx={{ position: 'absolute', left: 16 }}
        >
          <ChevronLeftIcon width={28} height={28} color="white" />
        </IconButton>
        <Box
          component="img"
          src={src}
          alt={item.caption ?? ''}
          sx={{ maxWidth: '90vw', maxHeight: '80vh', objectFit: 'contain' }}
        />
        <IconButton
          tooltip="Next"
          shortcut="→"
          aria-label="Next"
          onClick={next}
          disabled={index >= items.length - 1}
          sx={{ position: 'absolute', right: 16 }}
        >
          <ChevronRightIcon width={28} height={28} color="white" />
        </IconButton>
      </Stack>
      {item.caption && (
        <Typography
          level="body-sm"
          sx={{ color: 'common.white', textAlign: 'center', p: 2 }}
          onClick={(e) => e.stopPropagation()}
        >
          {item.caption}
        </Typography>
      )}
    </Box>
  );
}

export default Lightbox;
