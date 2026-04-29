'use client';
/**
 * @file app/app/galleries/page.tsx
 * @brief Editorial galleries page — oversized serif masthead, sticky glass
 *        toolbar, magazine-style hero spread, bento mosaic of cards. Drawer +
 *        lightbox routing preserved (?gallery= / ?item=).
 */
import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { motion } from 'framer-motion';
import { Button, Drawer, EmptyState, Skeleton, Avatar, Chip, IconButton } from '@/components/ui';
import { TrashIcon } from '@heroicons/react/24/outline';
import { GalleryCard } from '@/components/galleries/GalleryCard';
import { GalleryCreateModal } from '@/components/galleries/GalleryCreateModal';
import { GallerySearchBar } from '@/components/galleries/GallerySearchBar';
import { GallerySortSelect, type SortOption } from '@/components/galleries/GallerySortSelect';
import { GalleryUpload } from '@/components/galleries/GalleryUpload';
import { MediaThumb } from '@/components/galleries/MediaThumb';
import { Lightbox } from '@/components/galleries/Lightbox';
import { PageMasthead } from '@/components/layout/PageMasthead';
import {
  useGalleryDetail,
  useGalleryItems,
  useGalleryList,
  useUpdateGallery,
  useDeleteGallery,
  useRemoveItem,
} from '@/hooks/useGalleries';
import { useSession } from '@/stores/session';
import { useConfirmDialog } from '@/stores/confirmDialog';
import { API_BASE } from '@/lib/auth/session';
import type { Gallery, ListGalleriesParams } from '@/lib/api/galleries';

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
    sort,
  };

  const { data: featuredData } = useGalleryList({ featured: true, sort: 'popular' });
  const { data: listData, isLoading: listLoading, error: listError } = useGalleryList(listParams);

  const featured = featuredData?.items ?? [];
  const featuredHero = featured[0];
  const featuredRail = featured.slice(1, 4);

  const totalCount = listData?.items.length ?? 0;

  return (
    <Box
      sx={{
        position: 'relative',
        minHeight: '100vh',
        px: { xs: 2, md: 6, lg: 8 },
        pb: 10,
        width: '100%',
      }}
    >
      <Box sx={{ position: 'relative', zIndex: 1 }}>
        <PageMasthead
          title="Galleries"
          meta={`${totalCount} ${totalCount === 1 ? 'collection' : 'collections'} on file`}
          right={<Button onClick={() => setCreateOpen(true)}>+ New gallery</Button>}
        />


        {/* ─── Sticky toolbar ───────────────────────────────────── */}
        <Box
          sx={{
            position: 'sticky',
            top: 0,
            zIndex: 5,
            mx: { xs: -2, md: -6, lg: -8 },
            px: { xs: 2, md: 6, lg: 8 },
            py: 1.5,
            backdropFilter: 'saturate(140%) blur(12px)',
            WebkitBackdropFilter: 'saturate(140%) blur(12px)',
            background:
              'color-mix(in srgb, var(--joy-palette-background-body) 78%, transparent)',
            borderTop: '1px solid var(--joy-palette-divider)',
            borderBottom: '1px solid var(--joy-palette-divider)',
            mb: { xs: 4, md: 6 },
          }}
        >
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={{ xs: 1, sm: 3 }}
            alignItems={{ sm: 'center' }}
            justifyContent="space-between"
          >
            <Box sx={{ flex: 1, minWidth: 0, '& > *': { mb: '0 !important' } }}>
              <GallerySearchBar onSearch={setSearchQuery} />
            </Box>
            <Box sx={{ '& > *': { mb: '0 !important' } }}>
              <GallerySortSelect sort={sort} onSortChange={setSort} />
            </Box>
          </Stack>
        </Box>

        {/* ─── Featured spread ─────────────────────────────────── */}
        {featuredHero && (
          <Box sx={{ mb: { xs: 6, md: 9 } }}>
            <SectionLabel index="01" label="Featured" italic="this season" />
            <Box
              sx={{
                mt: 3,
                display: 'grid',
                gap: { xs: 1.5, md: 2.5 },
                gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' },
                gridTemplateRows: { md: 'repeat(3, 1fr)' },
                minHeight: { md: 540 },
              }}
            >
              <FeaturedHero gallery={featuredHero} onSelect={select} />
              {featuredRail.map((g) => (
                <FeaturedSide key={g.id} gallery={g} onSelect={select} />
              ))}
            </Box>
          </Box>
        )}

        {/* ─── Main mosaic ─────────────────────────────────────── */}
        <Box>
          <SectionLabel
            index="02"
            label={searchQuery ? 'Results' : 'All collections'}
            italic={searchQuery ? `for "${searchQuery}"` : 'most recent first'}
          />
          <Box sx={{ mt: 3 }}>
            <GalleryMosaic
              data={listData}
              isLoading={listLoading}
              error={listError}
              onSelect={select}
              onEmptyAction={() => router.push('/app/media')}
            />
          </Box>
        </Box>
      </Box>

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

/* ─────────────────────────────────────────────────────────────────
 * Section label — small caps numeral + italic kicker
 * ───────────────────────────────────────────────────────────────── */
function SectionLabel({ index, label, italic }: { index: string; label: string; italic?: string }) {
  return (
    <Stack direction="row" alignItems="baseline" spacing={2} sx={{ borderBottom: '1px solid', borderColor: 'divider', pb: 1.5 }}>
      <Typography
        sx={{
          fontFamily: 'var(--font-display)',
          fontVariantNumeric: 'tabular-nums',
          fontSize: '11px',
          letterSpacing: '0.2em',
          color: 'text.tertiary',
        }}
      >
        {index}
      </Typography>
      <Typography
        sx={{
          fontFamily: 'var(--font-display)',
          fontSize: { xs: '22px', md: '28px' },
          fontWeight: 400,
          letterSpacing: '-0.01em',
        }}
      >
        {label}
      </Typography>
      {italic && (
        <Typography
          sx={{
            fontFamily: 'var(--font-display)',
            fontStyle: 'italic',
            fontSize: { xs: '14px', md: '16px' },
            color: 'text.tertiary',
            ml: 'auto !important',
          }}
        >
          {italic}
        </Typography>
      )}
    </Stack>
  );
}

/* ─────────────────────────────────────────────────────────────────
 * Featured hero — large dominant tile (spans 3 rows on md)
 * ───────────────────────────────────────────────────────────────── */
function FeaturedHero({ gallery, onSelect }: { gallery: Gallery; onSelect: (id: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      style={{ gridRow: 'span 3', display: 'flex' }}
    >
      <Box
        role="button"
        tabIndex={0}
        onClick={() => onSelect(gallery.id)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect(gallery.id);
          }
        }}
        sx={{
          position: 'relative',
          flex: 1,
          minHeight: 360,
          borderRadius: 'lg',
          overflow: 'hidden',
          cursor: 'pointer',
          background:
            'linear-gradient(135deg, var(--joy-palette-neutral-200) 0%, var(--joy-palette-neutral-100) 100%)',
          boxShadow: '0 12px 40px -16px rgba(0,0,0,0.35)',
          transition: 'transform 600ms cubic-bezier(0.22,1,0.36,1), box-shadow 400ms',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: '0 20px 60px -20px rgba(0,0,0,0.45)',
          },
          '&:hover .nx-thumb': { transform: 'scale(1.04)' },
        }}
      >
        <MediaThumb mediaId={gallery.cover_media_id} alt={`${gallery.title} cover`} zoomOnHover />

        {/* gradient veil */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.0) 35%, rgba(0,0,0,0.65) 100%)',
          }}
        />
        {/* corner badge */}
        {gallery.is_featured && (
          <Box sx={{ position: 'absolute', top: 20, left: 20 }}>
            <Chip size="sm" color="warning" variant="solid">
              Featured
            </Chip>
          </Box>
        )}
        {/* footer */}
        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 0, p: { xs: 3, md: 4 } }}>
          <Typography
            level="body-xs"
            sx={{
              fontFamily: 'var(--font-display)',
              fontStyle: 'italic',
              color: 'rgba(255,255,255,0.78)',
              mb: 0.5,
            }}
          >
            Cover story
          </Typography>
          <Typography
            sx={{
              fontFamily: 'var(--font-display)',
              fontWeight: 400,
              fontSize: { xs: '32px', md: '46px' },
              lineHeight: 1.02,
              letterSpacing: '-0.02em',
              color: '#fff',
              mb: 1.5,
              textShadow: '0 2px 24px rgba(0,0,0,0.35)',
            }}
          >
            {gallery.title}
          </Typography>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Avatar
              sx={{ width: 22, height: 22, fontSize: '0.7rem' }}
              src={`${API_BASE}/api/v1/users/${gallery.owner_id}/avatar`}
              alt={gallery.owner_id}
            />
            <Typography level="body-xs" sx={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>
              {gallery.owner_id}
            </Typography>
            <Typography level="body-xs" sx={{ color: 'rgba(255,255,255,0.55)' }}>
              ·
            </Typography>
            <Typography level="body-xs" sx={{ color: 'rgba(255,255,255,0.7)' }}>
              {gallery.item_count} {gallery.item_count === 1 ? 'piece' : 'pieces'}
            </Typography>
          </Stack>
        </Box>
      </Box>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────────────────────────
 * Featured side — smaller stacked tile
 * ───────────────────────────────────────────────────────────────── */
function FeaturedSide({ gallery, onSelect }: { gallery: Gallery; onSelect: (id: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay: 0.06 }}
      style={{ display: 'flex' }}
    >
      <Box
        role="button"
        tabIndex={0}
        onClick={() => onSelect(gallery.id)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect(gallery.id);
          }
        }}
        sx={{
          position: 'relative',
          flex: 1,
          minHeight: 0,
          borderRadius: 'md',
          overflow: 'hidden',
          cursor: 'pointer',
          background: 'var(--joy-palette-neutral-100)',
          transition: 'transform 400ms ease',
          '&:hover .nx-thumb': { transform: 'scale(1.05)' },
        }}
      >
        <MediaThumb mediaId={gallery.cover_media_id} alt={`${gallery.title} cover`} zoomOnHover />

        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.62) 100%)',
          }}
        />
        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 0, p: 2 }}>
          <Typography
            sx={{
              fontFamily: 'var(--font-display)',
              fontSize: '20px',
              lineHeight: 1.1,
              color: '#fff',
              fontWeight: 500,
            }}
            noWrap
          >
            {gallery.title}
          </Typography>
          <Typography level="body-xs" sx={{ color: 'rgba(255,255,255,0.7)', mt: 0.25 }}>
            {gallery.item_count} {gallery.item_count === 1 ? 'piece' : 'pieces'}
          </Typography>
        </Box>
      </Box>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────────────────────────
 * Mosaic grid — bento layout, every 5th tile spans 2 cols (16/9)
 * ───────────────────────────────────────────────────────────────── */
function GalleryMosaic({
  data,
  isLoading,
  error,
  onSelect,
  onEmptyAction,
}: {
  data: { items: Gallery[] } | undefined;
  isLoading: boolean;
  error: unknown;
  onSelect: (id: string) => void;
  onEmptyAction: () => void;
}) {
  if (error) {
    return (
      <EmptyState
        title="Couldn't load galleries"
        description={String(error)}
        action={
          <Button variant="soft" onClick={() => window.location.reload()}>
            Retry
          </Button>
        }
      />
    );
  }
  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' },
        }}
      >
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <Skeleton key={i} height={i % 5 === 0 ? 280 : 220} />
        ))}
      </Box>
    );
  }
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No galleries yet"
        description="Create one to share photos."
        action={
          <Button variant="solid" onClick={onEmptyAction}>
            Browse media
          </Button>
        }
      />
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gap: { xs: 1.5, md: 2.5 },
        gridTemplateColumns: {
          xs: 'repeat(2, 1fr)',
          md: 'repeat(3, 1fr)',
          lg: 'repeat(4, 1fr)',
          xl: 'repeat(5, 1fr)',
        },
        gridAutoFlow: 'dense',
      }}
    >
      {data.items.map((g, idx) => {
        const wide = idx % 5 === 0 && idx !== 0;
        return (
          <motion.div
            key={g.id}
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.32, delay: Math.min(idx * 0.02, 0.3) }}
            style={{ gridColumn: wide ? 'span 2' : undefined }}
          >
            <Box
              sx={
                wide
                  ? {
                      '& > div > div:first-of-type': { aspectRatio: '16/9 !important' },
                    }
                  : undefined
              }
            >
              <GalleryCard gallery={g} onSelect={onSelect} />
            </Box>
          </motion.div>
        );
      })}
    </Box>
  );
}

/* ─────────────────────────────────────────────────────────────────
 * Drawer — gallery items grid (preserved behavior)
 * ───────────────────────────────────────────────────────────────── */
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
  const sessionUser = useSession((s) => s.user);
  const confirm = useConfirmDialog((s) => s.confirm);
  const updateMut = useUpdateGallery();
  const deleteMut = useDeleteGallery();
  const removeItemMut = useRemoveItem(galleryId ?? '');

  const isOwner = !!gallery && !!sessionUser && gallery.owner_id === sessionUser.id;
  const canContribute =
    isOwner ||
    (!!gallery &&
      (gallery.contribution_policy === 'community' ||
        gallery.contribution_policy === 'collaborators'));

  const handleDelete = async () => {
    if (!gallery) return;
    const ok = await confirm({
      title: `Delete gallery?`,
      message: `Delete "${gallery.title}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      tone: 'danger',
    });
    if (!ok) return;
    deleteMut.mutate(gallery.id, { onSuccess: () => onClose() });
  };

  const handleRemoveItem = async (e: React.MouseEvent, itemId: string) => {
    e.stopPropagation();
    const ok = await confirm({
      title: 'Remove item?',
      message: 'Remove this item from the gallery?',
      confirmLabel: 'Remove',
      tone: 'danger',
    });
    if (!ok) return;
    removeItemMut.mutate(itemId);
  };

  const visibilityOpts: Array<Gallery['visibility']> = ['private', 'subgroup', 'community'];
  const policyOpts: Array<Gallery['contribution_policy']> = [
    'owner_only',
    'collaborators',
    'community',
  ];

  return (
    <Drawer open={!!galleryId} onClose={onClose} title={gallery?.title ?? 'Gallery'} width={680}>
      {!gallery ? (
        <Skeleton height={200} />
      ) : (
        <Stack spacing={3}>
          {/* Header / actions */}
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Avatar
              src={`${API_BASE}/api/v1/users/${gallery.owner_id}/avatar`}
              alt={gallery.owner_id}
              sx={{ width: 32, height: 32 }}
            />
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography level="body-sm" sx={{ fontWeight: 500 }} noWrap>
                {gallery.owner_id}
              </Typography>
              <Typography level="body-xs" sx={{ color: 'text.tertiary' }}>
                {items?.length ?? 0} {(items?.length ?? 0) === 1 ? 'item' : 'items'}
              </Typography>
            </Box>
            {isOwner && (
              <IconButton
                size="sm"
                variant="plain"
                color="danger"
                onClick={handleDelete}
                disabled={deleteMut.isPending}
                aria-label="Delete gallery"
              >
                <TrashIcon style={{ width: 18, height: 18 }} />
              </IconButton>
            )}
          </Stack>

          {/* Description */}
          {gallery.description && (
            <Typography level="body-sm" sx={{ color: 'text.secondary' }}>
              {gallery.description}
            </Typography>
          )}

          {/* Scope / access */}
          <Box>
            <Typography
              level="body-xs"
              sx={{
                textTransform: 'uppercase',
                letterSpacing: '0.16em',
                color: 'text.tertiary',
                mb: 1,
              }}
            >
              Visibility
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {visibilityOpts.map((v) => {
                const active = gallery.visibility === v;
                return (
                  <Chip
                    key={v}
                    size="sm"
                    color={active ? 'primary' : 'neutral'}
                    variant={active ? 'solid' : 'soft'}
                    onClick={
                      isOwner && !active
                        ? () =>
                            updateMut.mutate({ id: gallery.id, body: { visibility: v } })
                        : undefined
                    }
                    sx={{ cursor: isOwner && !active ? 'pointer' : 'default' }}
                  >
                    {v}
                  </Chip>
                );
              })}
            </Stack>

            <Typography
              level="body-xs"
              sx={{
                textTransform: 'uppercase',
                letterSpacing: '0.16em',
                color: 'text.tertiary',
                mb: 1,
                mt: 2,
              }}
            >
              Who can contribute
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {policyOpts.map((p) => {
                const active = gallery.contribution_policy === p;
                return (
                  <Chip
                    key={p}
                    size="sm"
                    color={active ? 'primary' : 'neutral'}
                    variant={active ? 'solid' : 'soft'}
                    onClick={
                      isOwner && !active
                        ? () =>
                            updateMut.mutate({
                              id: gallery.id,
                              body: { contribution_policy: p },
                            })
                        : undefined
                    }
                    sx={{ cursor: isOwner && !active ? 'pointer' : 'default' }}
                  >
                    {p.replace('_', ' ')}
                  </Chip>
                );
              })}
            </Stack>
          </Box>

          {/* Upload */}
          {canContribute && (
            <Box>
              <Typography
                level="body-xs"
                sx={{
                  textTransform: 'uppercase',
                  letterSpacing: '0.16em',
                  color: 'text.tertiary',
                  mb: 1,
                }}
              >
                Add content
              </Typography>
              <GalleryUpload galleryId={gallery.id} />
            </Box>
          )}

          {/* Items */}
          <Box>
            <Typography
              level="body-xs"
              sx={{
                textTransform: 'uppercase',
                letterSpacing: '0.16em',
                color: 'text.tertiary',
                mb: 1,
              }}
            >
              Items
            </Typography>
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
                    sx={{
                      position: 'relative',
                      aspectRatio: '1',
                      borderRadius: 'sm',
                      overflow: 'hidden',
                      cursor: 'pointer',
                      background: 'var(--joy-palette-neutral-100)',
                      transition: 'transform 240ms ease, opacity 240ms ease',
                      '&:hover': { transform: 'scale(1.02)', opacity: 0.95 },
                      '&:hover .nx-item-del': { opacity: 1 },
                    }}
                    role="button"
                    tabIndex={0}
                    onClick={() => onOpenItem(idx)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onOpenItem(idx);
                      }
                    }}
                    aria-label={it.caption ?? `Item ${idx + 1}`}
                  >
                    <MediaThumb mediaId={it.media_id} alt={it.caption ?? `Item ${idx + 1}`} />
                    {isOwner && (
                      <IconButton
                        className="nx-item-del"
                        size="sm"
                        variant="solid"
                        color="danger"
                        onClick={(e) => handleRemoveItem(e, it.id)}
                        aria-label="Remove item"
                        sx={{
                          position: 'absolute',
                          top: 4,
                          right: 4,
                          opacity: 0,
                          transition: 'opacity 180ms ease',
                          minHeight: 24,
                          minWidth: 24,
                          padding: '4px',
                        }}
                      >
                        <TrashIcon style={{ width: 14, height: 14 }} />
                      </IconButton>
                    )}
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </Stack>
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
