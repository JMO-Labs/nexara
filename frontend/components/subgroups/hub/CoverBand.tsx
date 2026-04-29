/**
 * @file components/subgroups/hub/CoverBand.tsx
 * @brief Full-bleed cover band with media or gradient fallback + title overlay.
 */
'use client';

import * as React from 'react';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import { MediaThumb } from '@/components/galleries/MediaThumb';
import { gradientFor } from '@/lib/groupVisuals';
import type { SubgroupDetail } from '@/lib/api/subgroups';

export interface CoverBandProps {
  subgroup: SubgroupDetail;
  right?: React.ReactNode;
}

export function CoverBand({ subgroup, right }: CoverBandProps) {
  const { background } = gradientFor(subgroup.slug);
  const hasCover = !!subgroup.cover_media_id;

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: { xs: 240, sm: 280, md: 360 },
        background: hasCover ? undefined : background,
        overflow: 'hidden',
        mb: 3,
      }}
    >
      {hasCover && <MediaThumb mediaId={subgroup.cover_media_id} alt={subgroup.name} />}

      {/* Strengthened veil gradient for text legibility */}
      <Box
        aria-hidden
        sx={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '60%',
          background: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.15) 40%, rgba(0,0,0,0.65) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Title + meta overlay */}
      <Box
        sx={{
          position: 'absolute',
          bottom: { xs: 16, sm: 20, md: 24 },
          left: { xs: 16, sm: 20, md: 24 },
          right: { xs: 16, sm: 20, md: 24 },
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          gap: 2,
        }}
      >
        <Box sx={{ flex: 1 }}>
          <Typography
            level="h1"
            sx={{
              fontSize: { xs: '2rem', sm: '2.5rem', md: '3rem', lg: '3.5rem' },
              fontFamily: 'var(--font-display)',
              color: '#fff',
              marginBottom: '8px',
              textShadow: '0 2px 24px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.5)',
            }}
          >
            {subgroup.name}
          </Typography>
          <Typography
            level="body-sm"
            sx={{
              color: '#fff',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              fontSize: '0.75rem',
              textShadow: '0 1px 2px rgba(0,0,0,0.5)',
            }}
          >
            {subgroup.member_count} members · {subgroup.is_private ? 'private' : 'public'}
          </Typography>
        </Box>
        {right && <Box sx={{ flexShrink: 0 }}>{right}</Box>}
      </Box>
    </Box>
  );
}

export default CoverBand;
