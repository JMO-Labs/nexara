'use client';
/**
 * @file components/subgroups/hub/MediaTab.tsx
 * @brief Media tab: grid of media from posts, galleries, and events with source filtering.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Chip from '@mui/joy/Chip';
import { AnimatePresence, motion } from 'framer-motion';
import { EmptyState, Skeleton } from '@/components/ui';
import { MediaThumb } from '@/components/galleries/MediaThumb';
import { useSubgroupMedia } from '@/hooks/useSubgroupMedia';
import type { SubgroupDetail } from '@/lib/api/subgroups';

export interface MediaTabProps {
  subgroup: SubgroupDetail;
}

type Source = 'all' | 'post' | 'gallery' | 'event';

export function MediaTab({ subgroup }: MediaTabProps) {
  const [source, setSource] = React.useState<Source>('all');

  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage, error } =
    useSubgroupMedia({
      slug: subgroup.slug,
      source,
      limit: 60,
    });

  const items = data?.pages.flatMap((p) => p.items) ?? [];

  // Source filter chips
  const sourceOptions: { label: string; value: Source }[] = [
    { label: 'All', value: 'all' },
    { label: 'Posts', value: 'post' },
    { label: 'Galleries', value: 'gallery' },
    { label: 'Events', value: 'event' },
  ];

  const sentinelRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!sentinelRef.current || !hasNextPage || isFetchingNextPage || isLoading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, isLoading, fetchNextPage]);

  if (error) {
    return (
      <EmptyState
        title="Couldn't load media"
        description={String(error)}
      />
    );
  }

  return (
    <Stack spacing={2}>
      {/* Source filter chips */}
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {sourceOptions.map((opt) => (
          <Chip
            key={opt.value}
            color={source === opt.value ? 'primary' : 'neutral'}
            variant={source === opt.value ? 'solid' : 'outlined'}
            onClick={() => setSource(opt.value)}
            slotProps={{ action: { sx: { cursor: 'pointer' } } }}
          >
            {opt.label}
          </Chip>
        ))}
      </Box>

      {/* Media grid */}
      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.div
            key="sk"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <Box
              sx={{
                display: 'grid',
                gap: 2,
                gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' },
              }}
            >
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <Box
                  key={i}
                  sx={{
                    position: 'relative',
                    paddingBottom: '100%',
                    overflow: 'hidden',
                    borderRadius: 'md',
                  }}
                >
                  <Skeleton />
                </Box>
              ))}
            </Box>
          </motion.div>
        ) : items.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <EmptyState
              title="No media yet"
              description={
                source === 'all'
                  ? 'Share photos and videos from posts, galleries, and events.'
                  : `No media from ${source}s yet.`
              }
            />
          </motion.div>
        ) : (
          <motion.div
            key="ct"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <Box
              sx={{
                display: 'grid',
                gap: 2,
                gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' },
              }}
            >
              {items.map((item) => (
                <motion.div
                  key={item.media_id}
                  layout
                  role="button"
                  tabIndex={0}
                  aria-label={`${item.source_title || 'media'}`}
                >
                  <Box
                    sx={{
                      position: 'relative',
                      paddingBottom: '100%',
                      overflow: 'hidden',
                      borderRadius: 'md',
                      cursor: 'pointer',
                      bgcolor: 'neutral.200',
                      '&:hover': {
                        opacity: 0.8,
                      },
                      transition: 'opacity 200ms',
                    }}
                  >
                    <MediaThumb
                      mediaId={item.media_id}
                      alt={item.media.alt_text || `${item.source_title || 'Media'}`}
                      zoomOnHover
                    />
                  </Box>
                </motion.div>
              ))}
            </Box>
            {isFetchingNextPage && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                <Skeleton width={40} height={40} />
              </Box>
            )}
            <div ref={sentinelRef} style={{ height: 1 }} />
          </motion.div>
        )}
      </AnimatePresence>
    </Stack>
  );
}

export default MediaTab;
