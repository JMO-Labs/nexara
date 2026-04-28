'use client';
/**
 * @file app/app/galleries/page.tsx
 * @brief Galleries grid + search + sort + featured row + drawer detail with lightbox.
 */
import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Button, Drawer, EmptyState, Skeleton } from '@/components/ui';
import { GalleryGrid } from '@/components/galleries/GalleryGrid';
import { GalleryCreateModal } from '@/components/galleries/GalleryCreateModal';
import { GallerySearchBar } from '@/components/galleries/GallerySearchBar';
import { GallerySortSelect, type SortOption } from '@/components/galleries/GallerySortSelect';
import { Lightbox } from '@/components/galleries/Lightbox';
import { useGalleryDetail, useGalleryItems, useGalleryList } from '@/hooks/useGalleries';
import { API_BASE } from '@/lib/auth/session';
import type { ListGalleriesParams } from '@/lib/api/galleries';

export default function GalleriesPage() {
  const router = useRouter();
  const params = useSearchParams();
  const galleryId = params.get('gallery');
  const itemIdx = params.get('item');
  const [createOpen, setCreateOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [sort, setSort] = React.useState<SortOption>('recent');

  const setParam = (next: URLSearchParams) =>
    router.push(next.toString() ? `/app/galleries?${next}` : '/app/galleries');

  const select = (id: string) => {
    const next = new URLSearchParams(params.toString());
    next.set('gallery', id);
    setParam(next);
  };
  const closeDrawer = () => {
    const next = new URLSearchParams(params.toString());
    next.delete('gallery');
    next.delete('item');
    setParam(next);
  };
  const openItem = (idx: number) => {
    const next = new URLSearchParams(params.toString());
    next.set('item', String(idx));
    setParam(next);
  };
  const closeItem = () => {
    const next = new URLSearchParams(params.toString());
    next.delete('item');
    setParam(next);
  };
  const setItemIndex = (idx: number) => {
    const next = new URLSearchParams(params.toString());
    next.set('item', String(idx));
    setParam(next);
  };

  const listParams: ListGalleriesParams = {
    q: searchQuery || undefined,
    sort: sort,
  };

  const featuredParams: ListGalleriesParams = {
    featured: true,
    sort: 'popular',
  };

  const { data: featuredData } = useGalleryList(featuredParams);

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 3 }}>
        <Typography level="h2" sx={{ fontFamily: 'var(--font-display)' }}>
          Galleries
        </Typography>
        <Button onClick={() => setCreateOpen(true)}>New gallery</Button>
      </Stack>

      <GallerySearchBar onSearch={setSearchQuery} />
      <GallerySortSelect sort={sort} onSortChange={setSort} />

      {/* Featured row */}
      {featuredData && featuredData.items.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography
            level="body-xs"
            sx={{
              fontSize: '11px',
              letterSpacing: '0.16em',
              textTransform: 'uppercase',
              color: 'text.tertiary',
              mb: 2,
            }}
          >
            Featured
          </Typography>
          <Box
            sx={{
              display: 'flex',
              gap: 2,
              overflowX: 'auto',
              pb: 1,
              '&::-webkit-scrollbar': {
                height: 4,
              },
              '&::-webkit-scrollbar-track': {
                background: 'transparent',
              },
              '&::-webkit-scrollbar-thumb': {
                background: 'var(--joy-palette-neutral-400)',
                borderRadius: 2,
              },
            }}
          >
            {featuredData.items.map((g) => (
              <Box
                key={g.id}
                sx={{
                  flex: '0 0 320px',
                  cursor: 'pointer',
                }}
                onClick={() => select(g.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    select(g.id);
                  }
                }}
              >
                <Box
                  sx={{
                    aspectRatio: '4/3',
                    background: g.cover_media_id
                      ? `url(${API_BASE}/api/v1/media/${g.cover_media_id}/thumbnail) center/cover`
                      : 'var(--joy-palette-neutral-100)',
                    borderRadius: 'md',
                  }}
                />
                <Typography level="title-sm" sx={{ mt: 1 }} noWrap>
                  {g.title}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      <GalleryGrid onSelect={select} params={listParams} />
      <GalleryDrawer galleryId={galleryId} onClose={closeDrawer} onOpenItem={openItem} />
      {galleryId && itemIdx !== null && (
        <LightboxConnected
          galleryId={galleryId}
          index={Number(itemIdx)}
          onClose={closeItem}
          onIndexChange={setItemIndex}
        />
      )}
      <GalleryCreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </Box>
  );
}

function GalleryDrawer({
  galleryId,
  onClose,
  onOpenItem,
}: {
  galleryId: string | null;
  onClose: () => void;
  onOpenItem: (idx: number) => void;
}) {
  const { data: gallery } = useGalleryDetail(galleryId);
  const { data: items, isLoading } = useGalleryItems(galleryId);

  return (
    <Drawer open={!!galleryId} onClose={onClose} title={gallery?.title ?? 'Gallery'} width={640}>
      {isLoading && <Skeleton height={200} />}
      {!isLoading && (!items || items.length === 0) && (
        <EmptyState title="No items yet" description="Add media to this gallery." />
      )}
      {items && items.length > 0 && (
        <Box
          sx={{
            display: 'grid',
            gap: 1,
            gridTemplateColumns: 'repeat(3, 1fr)',
          }}
        >
          {items.map((it, idx) => (
            <Box
              key={it.id}
              role="button"
              tabIndex={0}
              onClick={() => onOpenItem(idx)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onOpenItem(idx);
                }
              }}
              sx={{
                aspectRatio: '1',
                background: `url(${API_BASE}/api/v1/media/${it.media_id}/thumbnail) center/cover`,
                borderRadius: 'sm',
                cursor: 'pointer',
              }}
              aria-label={it.caption ?? `Item ${idx + 1}`}
            />
          ))}
        </Box>
      )}
    </Drawer>
  );
}

function LightboxConnected({
  galleryId,
  index,
  onClose,
  onIndexChange,
}: {
  galleryId: string;
  index: number;
  onClose: () => void;
  onIndexChange: (i: number) => void;
}) {
  const { data: items } = useGalleryItems(galleryId);
  if (!items || items.length === 0) return null;
  return <Lightbox items={items} index={index} onClose={onClose} onIndexChange={onIndexChange} />;
}
