'use client';
/**
 * @file components/galleries/GalleryGrid.tsx
 * @brief Responsive grid of GalleryCards.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import { Skeleton, EmptyState } from '@/components/ui';
import { GalleryCard } from './GalleryCard';
import { useGalleryList } from '@/hooks/useGalleries';

export interface GalleryGridProps {
  onSelect: (id: string) => void;
}

export function GalleryGrid({ onSelect }: GalleryGridProps) {
  const { data, isLoading, error } = useGalleryList();

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' },
        }}
      >
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={220} />
        ))}
      </Box>
    );
  }
  if (error) return <EmptyState title="Couldn't load galleries" description={String(error)} />;
  if (!data || data.items.length === 0) {
    return <EmptyState title="No galleries yet" description="Create one to share photos." />;
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gap: 2,
        gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' },
      }}
    >
      {data.items.map((g) => (
        <GalleryCard key={g.id} gallery={g} onSelect={onSelect} />
      ))}
    </Box>
  );
}

export default GalleryGrid;
