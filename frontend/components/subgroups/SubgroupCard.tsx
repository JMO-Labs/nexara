'use client';
/**
 * @file components/subgroups/SubgroupCard.tsx
 * @brief Editorial group tile. Per-slug deterministic gradient gives each
 *        group a stable color identity (no cover-media field exists on
 *        Subgroup). Click selects, secondary button joins/leaves.
 */
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Button, Chip } from '@/components/ui';
import { MediaThumb } from '@/components/galleries/MediaThumb';
import type { Subgroup } from '@/lib/api/subgroups';
import { gradientFor, monogram } from '@/lib/groupVisuals';

export interface SubgroupCardProps {
  subgroup: Subgroup;
  memberCount?: number;
  isMember?: boolean;
  onSelect: (slug: string) => void;
  onJoin?: (slug: string) => void;
  onLeave?: (slug: string) => void;
  busy?: boolean;
  /** Anchor tile = taller hero variant (used in bento mosaic). */
  anchor?: boolean;
}

export function SubgroupCard({
  subgroup,
  memberCount,
  isMember,
  onSelect,
  onJoin,
  onLeave,
  busy,
  anchor,
}: SubgroupCardProps) {
  const router = useRouter();
  const { background, monogramBg } = React.useMemo(
    () => gradientFor(subgroup.slug),
    [subgroup.slug],
  );
  const handleClick = () => onSelect(subgroup.slug);

  const getCtaButton = () => {
    if (isMember) {
      return (
        <Button
          variant="soft"
          color="neutral"
          size="sm"
          loading={busy}
          onClick={(e) => {
            e.stopPropagation();
            onLeave?.(subgroup.slug);
          }}
          sx={{
            bgcolor: 'rgba(255,255,255,0.14)',
            color: '#fff',
            '&:hover': { bgcolor: 'rgba(255,255,255,0.22)' },
          }}
        >
          Leave
        </Button>
      );
    }

    if (subgroup.join_policy === 'invite_only') {
      return (
        <Button
          size="sm"
          disabled
          sx={{
            bgcolor: 'rgba(255,255,255,0.14)',
            color: '#fff',
            '&:disabled': { opacity: 0.5 },
          }}
        >
          Invite required
        </Button>
      );
    }

    if (subgroup.join_policy === 'admin_approval') {
      return (
        <Button
          size="sm"
          loading={busy}
          onClick={(e) => {
            e.stopPropagation();
            onJoin?.(subgroup.slug);
          }}
          sx={{
            bgcolor: '#fff',
            color: 'rgba(0,0,0,0.85)',
            '&:hover': { bgcolor: 'rgba(255,255,255,0.88)' },
          }}
        >
          Request to join
        </Button>
      );
    }

    return (
      <Button
        size="sm"
        loading={busy}
        onClick={(e) => {
          e.stopPropagation();
          onJoin?.(subgroup.slug);
        }}
        sx={{
          bgcolor: '#fff',
          color: 'rgba(0,0,0,0.85)',
          '&:hover': { bgcolor: 'rgba(255,255,255,0.88)' },
        }}
      >
        Join
      </Button>
    );
  };

  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      sx={{
        position: 'relative',
        minHeight: anchor ? { xs: 320, md: 420 } : { xs: 220, md: 260 },
        height: '100%',
        borderRadius: 'lg',
        overflow: 'hidden',
        cursor: 'pointer',
        background,
        color: 'rgba(255,255,255,0.92)',
        boxShadow: '0 10px 36px -18px rgba(0,0,0,0.55)',
        transition:
          'transform 600ms cubic-bezier(0.22,1,0.36,1), box-shadow 400ms ease',
        '&:hover': {
          transform: 'translateY(-3px)',
          boxShadow: '0 22px 60px -22px rgba(0,0,0,0.65)',
        },
        '&:hover .nx-grain': { opacity: 0.18 },
        '&:hover .nx-mono': { transform: 'rotate(-3deg) scale(1.04)' },
        '&:hover .nx-thumb': { transform: 'scale(1.04)' },
      }}
    >
      {/* cover image (replaces gradient when present) */}
      {subgroup.cover_media_id && (
        <MediaThumb mediaId={subgroup.cover_media_id} alt={subgroup.name} zoomOnHover />
      )}
      {/* darker scrim to keep text legible over photo backgrounds */}
      {subgroup.cover_media_id && (
        <Box
          aria-hidden
          sx={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(180deg, rgba(0,0,0,0.18) 0%, rgba(0,0,0,0.05) 35%, rgba(0,0,0,0.65) 100%)',
            pointerEvents: 'none',
          }}
        />
      )}
      {/* grain veil */}
      <Box
        aria-hidden
        className="nx-grain"
        sx={{
          position: 'absolute',
          inset: 0,
          opacity: 0.1,
          mixBlendMode: 'overlay',
          transition: 'opacity 400ms ease',
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.6'/></svg>\")",
        }}
      />
      {/* corner monogram */}
      <Box
        className="nx-mono"
        aria-hidden
        sx={{
          position: 'absolute',
          top: anchor ? 24 : 18,
          left: anchor ? 24 : 18,
          width: anchor ? 64 : 48,
          height: anchor ? 64 : 48,
          borderRadius: '999px',
          background: monogramBg,
          color: 'rgba(0,0,0,0.78)',
          display: 'grid',
          placeItems: 'center',
          fontFamily: 'var(--font-display)',
          fontWeight: 500,
          fontSize: anchor ? 22 : 17,
          letterSpacing: '0.02em',
          transition: 'transform 400ms cubic-bezier(0.22,1,0.36,1)',
        }}
      >
        {monogram(subgroup.name)}
      </Box>

      {/* meta strip top-right */}
      <Stack
        direction="row"
        spacing={0.75}
        sx={{ position: 'absolute', top: anchor ? 28 : 22, right: anchor ? 24 : 18 }}
      >
        {subgroup.is_private && (
          <Chip
            size="sm"
            variant="soft"
            sx={{
              bgcolor: 'rgba(255,255,255,0.16)',
              color: '#fff',
              backdropFilter: 'blur(6px)',
              fontFamily: 'var(--font-mono, var(--font-body))',
              fontSize: '10px',
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
            }}
          >
            Private
          </Chip>
        )}
      </Stack>

      {/* footer block */}
      <Box
        sx={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          p: anchor ? { xs: 3, md: 4 } : { xs: 2.25, md: 2.75 },
          background:
            'linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.45) 70%, rgba(0,0,0,0.7) 100%)',
        }}
      >
        <Typography
          level="body-xs"
          sx={{
            fontFamily: 'var(--font-mono, var(--font-body))',
            fontSize: '10px',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.6)',
            mb: 0.75,
          }}
        >
          {subgroup.join_policy.replace('_', ' ')}
          {typeof memberCount === 'number' && (
            <>
              <Box component="span" sx={{ mx: 0.75, opacity: 0.4 }}>
                ·
              </Box>
              {memberCount} {memberCount === 1 ? 'member' : 'members'}
            </>
          )}
        </Typography>
        <Typography
          sx={{
            fontFamily: 'var(--font-display)',
            fontWeight: 400,
            fontSize: anchor
              ? { xs: '34px', md: '52px' }
              : { xs: '22px', md: '28px' },
            lineHeight: 1.02,
            letterSpacing: '-0.02em',
            color: '#fff',
            textShadow: '0 2px 22px rgba(0,0,0,0.35)',
            mb: subgroup.description ? 1 : 0,
          }}
        >
          {subgroup.name}
        </Typography>
        {subgroup.description && (
          <Typography
            level="body-sm"
            sx={{
              color: 'rgba(255,255,255,0.78)',
              display: '-webkit-box',
              WebkitLineClamp: anchor ? 3 : 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              maxWidth: anchor ? '78%' : '100%',
            }}
          >
            {subgroup.description}
          </Typography>
        )}
        <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
          {getCtaButton()}
          <Button
            variant="plain"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/app/subgroups/${subgroup.slug}`);
            }}
            sx={{
              color: 'rgba(255,255,255,0.78)',
              '&:hover': { color: '#fff', bgcolor: 'rgba(255,255,255,0.08)' },
            }}
          >
            Open →
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

export default SubgroupCard;
