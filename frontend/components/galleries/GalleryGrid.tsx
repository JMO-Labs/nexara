'use client';
/**
 * @file components/galleries/GalleryGrid.tsx
 * @brief Responsive grid of GalleryCards.
 */
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/joy/Box';
import { motion } from 'framer-motion';
import { Skeleton, EmptyState, Button } from '@/components/ui';
import { GalleryCard } from './GalleryCard';
import { useGalleryList } from '@/hooks/useGalleries';

export interface GalleryGridProps {
  onSelect: (id: string) => void;
}

export function GalleryGrid({ onSelect }: GalleryGridProps) {
  const router = useRouter();
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
  if (error)
    return (
      <EmptyState
        title="Couldn't load galleries"
        description={String(error)}
        action={<Button variant="soft" onClick={() => router.refresh()}>Retry</Button>}
      />
    );
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No galleries yet"
        description="Create one to share photos."
        action={<Button variant="solid" onClick={() => router.push('/app/media')}>Browse media</Button>}
      />
    );
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
        <motion.div key={g.id} layout>
          <GalleryCard gallery={g} onSelect={onSelect} />
        </motion.div>
      ))}
    </Box>
  );
}

export default GalleryGrid;
